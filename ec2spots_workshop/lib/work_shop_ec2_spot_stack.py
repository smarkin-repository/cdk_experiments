import aws_cdk as core
from aws_cdk import (
    Duration,
    Stack,
    # aws_sqs as sqs,
    aws_ec2 as ec2,
)
from constructs import Construct
from .base_network  import BaseNetworkEnv, EnvProps
from .ec2_spot import EC2Spot, EC2Props
from .web_asg import WebAsg, WebProps

class WorkshopEC2SpotStack(Stack):
    # TODO list mixed instance policy
    # - use spot but without mix
    def __init__(
            self, scope: Construct, construct_id: str, 
            env_props: EnvProps, 
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
    # TODO list
    # - пока трафик не идет черех ALB, попробовать через HTTP и пробросить cirdr_block от vpc
    # - allow traffic from ALB to ASG only + specific IPs
    # - setup web applicaiont on port 8080
    # - refactoring structure of project
    
    def __init__(self, scope: Construct, construct_id: str, env_props: EnvProps, props: WebProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        base_env = BaseNetworkEnv(self, f"${env_props.prefix}-base-network-env", env_props)
        base_env.create_ssm_endpoint()
        base_env.create_alb()
        props.vpc = base_env.vpc
        web_asg = WebAsg(self, f"${props.prefix}-web-asg-stack", props )
        web_asg.create_asg()
        base_env.add_target_group_for_alb(
            web_asg.asg, port=8080
        )

        # The code that defines your stack goes here