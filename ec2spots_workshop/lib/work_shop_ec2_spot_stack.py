from aws_cdk import (
    Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_route53 as route53,
    aws_elasticloadbalancingv2 as elbv2
)

from constructs import Construct
from .base_network  import BaseNetwork
from .ec2_spot import EC2Spot, EC2Props
from .web_asg import WebAsg
from .ecs import ECS
from .aws_framework import AWSFramework
from .props import WebAsgProps, ECSProps, ClusterProps
from .utils import get_my_external_ip


class WorkshopEC2SpotStack(Stack):
    # TODO list mixed instance policy
    # - use spot but without mix
    def __init__(
            self, scope: Construct, construct_id: str, 
            env_props, 
            ec2_type: str,
            ami_image: str, 
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        base_env = BaseNetwork(self, f"${env_props.prefix}-base-network-env", env_props)
        base_env.create_ssm_endpoint()
        ec2_props = EC2Props(
            ec2_type=ec2_type,
            ami_image=ami_image,
            vpc=base_env.vpc,
            env=env_props.env,
            prefix=env_props.prefix
        )
        EC2Spot(self, f"${env_props.prefix}-ec2-spot-stack", ec2_props )

class WorkshopWebAsgStack(Stack):
    def add_assets(self):
        self._web_asg.asset_user_data()
    
    def __init__(self, scope: Construct, construct_id: str, prefix: str, props: WebAsgProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        # [WARNING] aws-cdk-lib.aws_ec2.SubnetType#PRIVATE_WITH_NAT is deprecated.
        subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        base_env = BaseNetwork(
            self, f"{props.prefix}-base-network-env",
            prefix=prefix,
            props=props,
            region=self.region,
            account=self.account
        )
        base_env.create_vpc(is_natgw=True)
        base_env.create_endpoints(
            service_names=[
                "ssm",
                "ec2messages",
                "ssmmessages"
            ],
            subnets=subnets
        )

        props.vpc = base_env.vpc
        props.subnets = subnets
        props.sg = base_env.create_securety_group(
            name = "sg-asg-hosts",
            ports=[443, 8080, 3389], 
            allow_ip_addresses=[props.vpc.vpc_cidr_block, get_my_external_ip()]
            # allow_ip_addresses=[props.vpc.vpc_cidr_block]
        )
        self._web_asg = WebAsg(self, f"{props.prefix}-web-asg-stack", props )
        self._web_asg.create_asg()
        base_env.create_alb_with_connect_https_to(
            asg=self._web_asg.asg,
            port=443,
            port_target=8080,
            internet_facing=True
        )
        aws_framework = AWSFramework(self, f"{prefix}-framwork-web-asg")
        aws_framework.create_arecord(
            domain_name=props.domain_name,
            record_name=props.record_name,
            target=base_env.alb
        )
        # The code that defines your stack goes here

class WorkshopEnvStask(Stack):
    @property
    def vpc(self):
        return self._vpc
    
    @property
    def alb(self):
        return self._alb
    
    @property
    def acm_cert(self):
        return self._acm_certificate

    def __init__(self, scope: Construct, construct_id: str, prefix: str, props, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = prefix
        self._base_env = BaseNetwork(
            self, f"{self._prefix}-base-network-env", 
            prefix=self._prefix,
            props=props, 
            region=self.region, account=self.account)
        self._vpc = self._base_env.create_vpc(is_natgw=True)
        self._base_env.create_endpoints(
            service_names=props.endpoints,
            subnets=props.endpoint_subnets
        )

        aws_framework = AWSFramework(self, f"{prefix}-framwork-ecs-env")
        sg_alb = aws_framework.create_securety_group(
            id = f"{self._prefix}-sg-alb-hosts",
            name = f"{self._prefix}-sg-alb-hosts",
            vpc=self._vpc,
            ports=[443, 80, 8080, 3389], 
            allow_ip_addresses=[props.cidr_block, get_my_external_ip()]
        )

        # move to Env 
        self._acm_certificate = aws_framework.create_acm_certificate(
            domain_name=props.domain_name,
            hosted_zone_id=props.hosted_zone_id,
            subjects=[f"*.{props.domain_name}"]
        )

        # Application Load Balancer (ALB) with its own security group
        self._alb = self._base_env.create_alb(
            load_balancer_name=f"{self._prefix}-alb",
            sg_alb=sg_alb,
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            internet_facing=props.alb_internet_facing,
        )

class WorkshopECSStack(Stack):
    @property
    def cluster(self):
        return self._cluster
    
    @property
    def ecs(self):
        return self._ecs
    
    @property
    def asg(self):
        return self._asg


    """
    stack creates the following resources for the workshop.
    - 1 VPC with 6 subnets; 3 public and 3 private subnets
    - Application Load Balancer (ALB) with its own security group
    - Target Group and an ALB listener
    - Cloud9 Environment and its IAM Role
    - EC2 Launch template with necessary ECS config for bootstrapping the instances into the ECS cluster
    - ECR Repository
    """
    # TODO fix deletion EC2, the instance attached to public IP
    # devide on two stack: cluster and capasity
    def __init__(
        self, scope: Construct, construct_id: str, prefix: str, props: ECSProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = prefix
        # 1 VPC with 2 subnets; 1 public and 1 private subnets
        # look at WorkshopEnvStack
        # TODO find another way to provide VPC
        # _vpc = props.env_props.vpc
        # EC2 Launch template with necessary ECS config for bootstrapping the instances into the ECS cluster
        self._ecs = ECS(
            self, f"{self._prefix.capitalize()}-ecs-cluster", 
            prefix=self._prefix, 
            props=props.cluster_props 
        )
        aws_framework = AWSFramework(self, f"{prefix}-framwork-ecs-cluster")
        sg_asg = aws_framework.create_securety_group(
            id = f"{self._prefix}-sg-asg-hosts",
            name = f"{self._prefix}-sg-asg-hosts",
            vpc=props.cluster_props.vpc,
            ports=[443, 80, 8080, 3389], 
            allow_ip_addresses=[props.env_props.cidr_block, get_my_external_ip()]
        )

        self._asg = self._ecs.create_asg_for_ecs(
            securety_group=sg_asg,
            data_files=["user_data_ecs.sh"]
        )
        # ECS Cluster with its own Auto Scaling Group (ASG) and its own security group
        self._cluster =  self._ecs.create_cluster(
            autoscaling_group=self._asg
        )

        aws_framework.create_arecord(
            id=f"{self._prefix.capitalize()}-ecs-arecord",
            domain_name=props.env_props.domain_name,
            record_name=props.env_props.record_name,
            target=props.cluster_props.alb
        )
        # ? Cloud9 Environment and its IAM Role 

class WorkshopServiceStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, prefix: str, props: ClusterProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = prefix

        repo = ecr.Repository.from_repository_name(self, f"{self._prefix}-ecr-repo-simple", repository_name="base-repo")
        # add policy to use ecr repository

        image = ecs.ContainerImage.from_ecr_repository(repo, "latest")
        ecs_service = ECS(self, f"{self._prefix}-ecs-service", prefix=self._prefix, props=props)
        simple_service = ecs_service.create_service(
            cluster=props.cluster, 
            container_name="ecs-simple", 
            image=image
        )

        target = simple_service.load_balancer_target(
            container_name="ecs-simple",
            container_port=80,
            # protocol=elbv2.ApplicationProtocol.HTTPS
        )

        listener = elbv2.ApplicationListener(
            self, f"{self._prefix.capitalize()}-ALB-Listener",
            load_balancer=props.alb,
            port=443,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=[props.acm_cert],
        )

        health_check = elbv2.HealthCheck(
            interval=Duration.seconds(60),
            port="80",
            path="/",
            timeout=Duration.seconds(5)
        )

        # target_group = elbv2.ApplicationTargetGroup(
        #     self, f"{self._prefix.upper()}-ALB-TargetGroup",
        #     port=80,
        #     # vpc=vpc,  
        #     target_group_name=f"{self._prefix.upper()}-workshop-tg",
        #     targets=targets,
        #     target_type=elbv2.TargetType.INSTANCE,
        #     protocol=elbv2.ApplicationProtocol.HTTPS,
        #     health_check = health_check
        # )

        listener.add_targets(
            id=f"{self._prefix.capitalize()}-ALB-ECS-Targets",
            target_group_name=f"{self._prefix.upper()}-ecs-service-tg",
            targets=[target],
            health_check=health_check,
            # protocol=elbv2.ApplicationProtocol.HTTPS
            port=80
        )

        # # Target Group and an ALB listener
        # props.cluster_props.alb.add_listener(
        # )