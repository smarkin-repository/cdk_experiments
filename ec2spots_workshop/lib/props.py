import aws_cdk as core
from dataclasses import dataclass
from typing import List, Dict

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
class VPCProps:
    cidr_block: str
    vpc: core.aws_ec2.Vpc=None
    subnets: core.aws_ec2.SubnetSelection=None
    propertis: Dict=None
    alb_sg: core.aws_ec2.SecurityGroup=None

@dataclass
class ClusterProps:
    spot_types: List[str]=None
    instance_type: str=None
    min_capacity: int=0
    max_capacity: int=1
    desired_capacity: int=0
    ami_image: str=None
    data_path: str=None

@dataclass
class R53Props:
    domain_name: str=None
    record_name: str=None

@dataclass
class ECSProps:
    env: core.Environment=None
    vpc_props: VPCProps=None
    cluster_props: ClusterProps=None
    r53_props: R53Props=None
    