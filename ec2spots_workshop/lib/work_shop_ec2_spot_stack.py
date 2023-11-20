from aws_cdk import (
    Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
)

from constructs import Construct
from .base_network  import BaseNetworkEnv
from .ec2_spot import EC2Spot, EC2Props
from .web_asg import WebAsg
from .ecs import ECS
from .route53 import R53
from .props import WebAsgProps, ECSProps
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

        base_env = BaseNetworkEnv(self, f"${env_props.prefix}-base-network-env", env_props)
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
    
    def __init__(self, scope: Construct, construct_id: str, props: WebAsgProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        props.account = self.account
        props.region = self.region
        # [WARNING] aws-cdk-lib.aws_ec2.SubnetType#PRIVATE_WITH_NAT is deprecated.
        subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS)
        base_env = BaseNetworkEnv(self, f"{props.prefix}-base-network-env", props)
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
        route53 = R53(self, f"{props.prefix}-route53", props.prefix)
        route53.create_arecord(
            domain_name=props.domain_name,
            record_name=props.record_name,
            target=base_env.alb
        )
        # The code that defines your stack goes here

class WorkshopEnvStask(Stack):
    @property
    def vpc(self):
        return self._base_env.vpc

    def __init__(self, scope: Construct, construct_id: str, props: ECSProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        props.account = self.account
        props.region = self.region
        self._base_env = BaseNetworkEnv(self, f"{props.prefix}-base-network-env", props)
        self._base_env.create_endpoints(
            service_names=[
                "ecs",
                "ecs-agent",
                "ssm",
                "ecr.dkr"
            ],
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )


class WorkshopECSStack(Stack):
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
        self, scope: Construct, construct_id: str, props: ECSProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        props.account = self.account
        props.region = self.region
        # 1 VPC with 2 subnets; 1 public and 1 private subnets
        # look at WorkshopEnvStack
        # TODO find another way to provide VPC
        _vpc = props.vpc
        # EC2 Launch template with necessary ECS config for bootstrapping the instances into the ECS cluster
        ecs = ECS(self, f"{props.prefix}-ecs-stack", props )
        _asg = ecs.create_asg(vpc=_vpc)
        cluster = ecs.create_cluster(
            vpc=_vpc,
            autoscaling_group=_asg
        )
        # FIXME  поскольку кластре иззалирован то надо либо дать доступ в интерент publicIP 
        # либо пробросить доступ к ECR и туда положить образ
        # TODO prepare image and publis on ECR
        # TODO change creation service to get images from ECR
        
        # service = ecs.create_service(cluster, "ecs-simple")
        # # Application Load Balancer (ALB) with its own security group
        # # Target Group and an ALB listener
        # base_env.create_alb_with_connect_https_to(
        #     target=service,
        #     port=443,
        #     port_target=80,
        #     internet_facing=True
        # )
        # route53 = R53(self, f"{props.prefix}-route53", props.prefix)
        # route53.create_arecord(
        #     domain_name=props.domain_name,
        #     record_name=props.record_name,
        #     target=base_env.alb
        # )
        # ? Cloud9 Environment and its IAM Role 
