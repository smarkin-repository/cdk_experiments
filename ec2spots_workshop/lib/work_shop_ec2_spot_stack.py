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
from .route53 import R53
from .utils import get_my_external_ip

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
    # Works well for HTTP, but still need to improve for HTTPS
    # - replace account/region/env_props with env
    # - write tests
    # - next step ssm-stress.json
    # - aws ssm send-command --cli-input-json file://ssm-stress.json
    # -* support https protocol
    
    def __init__(self, scope: Construct, construct_id: str, env_props: EnvProps, props: WebProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        base_env = BaseNetworkEnv(self, f"{env_props.prefix}-base-network-env", env_props)
        base_env.create_ssm_endpoint()
        props.vpc = base_env.vpc
        web_asg = WebAsg(self, f"{props.prefix}-web-asg-stack", props )
        web_asg.create_asg()
        base_env.create_alb_with_connect_http_to(
            asg=web_asg.asg,
            port=80,
            port_target=8080,
            internet_facing=True
        )
        web_asg.asset_user_data(data_path="../data/scripts")
        route53 = R53(self, f"{env_props.prefix}-route53", env_props.prefix)
        route53.create_arecord(
            domain_name=props.domain_name,
            record_name=props.record_name,
            target=base_env.alb
        )
        # The code that defines your stack goes here