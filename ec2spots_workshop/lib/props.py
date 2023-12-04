"""
    Props for stacks
"""

import aws_cdk as core
from dataclasses import dataclass
from typing import List, Dict
from .ecs import ECS

@dataclass
class WebAsgProps:
    prefix: str
    cidr_block: str
    propertis: Dict
    vpc: core.aws_ec2.Vpc=None
    spot_types: List[str]=None
    instance_type: str=None
    min_capacity: int=0
    max_capacity: int=1
    desired_capacity: int=0
    ami_image: str=None
    domain_name: str=None
    record_name: str=None
    env: core.Environment=None
    data_path: str=None
    subnets: core.aws_ec2.SubnetSelection=None
    sg: core.aws_ec2.SecurityGroup=None

@dataclass
class EC2Props:
    ec2_type: str
    vpc: core.aws_ec2.Vpc
    env: core.Environment
    prefix: str
    ami_image: str

@dataclass
class EnvProps:
    cidr_block: str
    vpc: core.aws_ec2.Vpc=None
    max_avz: int=3
    endpoints : List=None
    endpoint_subnets: core.aws_ec2.SubnetSelection=None
    propertis: Dict=None
    alb_sg: core.aws_ec2.SecurityGroup=None
    alb_internet_facing: bool=False
    domain_name: str=None
    hosted_zone_id: str=None
    record_name: str=None

@dataclass
class ClusterProps:
    spot_types: List[str]=None
    instance_type: str=None
    min_capacity: int=0
    max_capacity: int=1
    desired_capacity: int=0
    ami_image: str=None
    data_path: str=None
    vpc: core.aws_ec2.Vpc=None
    alb: core.aws_elasticloadbalancingv2.ApplicationLoadBalancer=None
    subnets: core.aws_ec2.SubnetSelection=None
    ecs: ECS=None
    asg: core.aws_autoscaling.AutoScalingGroup=None
    cluster: core.aws_ecs.Cluster=None
    acm_cert: core.aws_certificatemanager.Certificate=None


@dataclass
class ECSProps:
    env: core.Environment=None
    env_props: EnvProps=None
    cluster_props: ClusterProps=None
    