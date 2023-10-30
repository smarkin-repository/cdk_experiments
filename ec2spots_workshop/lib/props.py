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

@dataclass
class EC2Props:
    ec2_type: str
    vpc: core.aws_ec2.Vpc
    env: core.Environment
    prefix: str
    ami_image: str