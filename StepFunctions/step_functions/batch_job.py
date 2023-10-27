from aws_cdk import (
    Aspects
    , Duration
    , Stack
    , Tags as Tag
    , aws_ec2 as ec2
    , aws_stepfunctions as sfn
    , aws_stepfunctions_tasks as sfn_tasks
    , aws_sns as sns
    , aws_sqs as sqs
    , aws_sns_subscriptions as subscriptions
    , aws_iam as iam
    , aws_batch as batch
)

from constructs import Construct

class BatchJob(Construct):
    def __init__(self, 
                scope: Construct, id: str,
                cidr_block: str="172.30.0.0/24",
                **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        # https://docs.aws.amazon.com/batch/latest/userguide/getting-started-ec2.html
        # prepare Batch Stack base on EC2 compute environment
        #1 create a compute Environment
        # Network Configuration
        #x VPC
        #x Subnets
        #? Security Group
        #x Private IP Address
        # create VPC
        self._vpc = ec2.Vpc(
            self, "VPC",
            vpc_name="vpc-workshop",
            ip_addresses=ec2.IpAddresses.cidr(cidr_block), 
            enable_dns_hostnames=True,
            enable_dns_support=True,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    name="private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                )
            ]
        )
        # Tag VPC
        # Aspects.of(self._vpc).add( Tag("Name", "vpc-workshop-lab"))
        # # Create ssm endpoint via AWS CDk
        # CodeWhisperer doesn't know CDK API documents
        # self._ssm_endpoint = SsmEndpoint(self, "SsmEndpoint", vpc=self._vpc)
        
        # import SG by ID
        security_group = ec2.SecurityGroup.from_security_group_id(
            self, "SG", 
            self._vpc.vpc_default_security_group,
            mutable=False
        )

        # ec2.InterfaceVpcEndpoint(
        #     self, "VPC Endpoint",
        #     vpc=self._vpc,
        #     service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self.region}.ssm", 443),
        #     # Choose which availability zones to place the VPC endpoint in, based on
        #     # available AZs
        #     subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        #     security_groups=[security_group]
        # )

        # IAM Rolessm Managed Policy 
        sts_assume_role_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["sts:AssumeRole"],
            resources=["*"]
        )
        batch_role = iam.Role(
            self, "BatchServiceRole", 
            assumed_by=iam.ServicePrincipal("batch.amazonaws.com")
        )
        batch_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSBatchServiceRole")
        )
        batch_role.add_to_policy(sts_assume_role_statement)
        # Instance Configuration
        #x instance role
        ## Launch Template
        #- Tags
        #- minimum vCPUs, Desired vCPUs, maximum vCPUs
        #- instance types
        #- Placement group?!
        #- Allocation strategy
        #- Image Type and Image Id

        instance_role = iam.Role(
            self, "InstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AmazonEC2ContainerServiceforEC2Role")
        )
        instance_role.add_to_policy(sts_assume_role_statement)

        instance_profile = iam.CfnInstanceProfile(
            self, "InstanceProfile",
            instance_profile_name="InstanceProfile",
            roles=[instance_role.role_name]
        )

        

        #2 Create a Job Queue

        #3 Create a Job Definition


        #4 Creat a Job

