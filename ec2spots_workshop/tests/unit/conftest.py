import pytest
import json
import os

from lib.work_shop_ec2_spot_stack import WorkshopWebAsgStack, WorkshopECSStack
from lib.props import WebAsgProps, ECSProps
from lib.utils import get_latest_linux_ami_from_aws, get_current_env

@pytest.fixture
def snapshot():
    # read json file from 'data' director
    with open(os.path.join(os.path.dirname(__file__), 'data', 'WorkShopEC2Spot.template.json')) as f:
        data = json.load(f) 
    return data


@pytest.fixture
def env():
    os.environ["CDK_DEFAULT_ACCOUNT"]="500480925365"
    os.environ["CDK_DEFAULT_REGION"]="us-east-1"
    return get_current_env()

@pytest.fixture
def web_props():
    ami_image = get_latest_linux_ami_from_aws(
        region="us-east-1"
        , pattern={
                "owner" : "amazon",
                "architecture" : "x86_64",
                "name" : "amzn2-ami-hvm-*"
        }
    )

    prefix = "workshop"
    return WebAsgProps(
        prefix=prefix
        , cidr_block="172.30.0.0/24"
        , propertis={
            "create_internet_gateway":True,
            "enable_dns_hostnames":True,
            "enable_dns_support":True,
        }
        , instance_type="t3.small"
        , spot_types=[
            "t3.small"
            ,"t4g.small"
        ]
        , min_capacity=1
        , max_capacity=2
        , desired_capacity=1
        , ami_image=ami_image
        , domain_name="taloni.link"
        , record_name="test"
        , data_path="../data"
    )

@pytest.fixture
def ecs_props():
    prefix = "workshop"
    ecs_props = ECSProps(
        prefix=prefix
        , cidr_block="172.30.0.0/24"
        , propertis={
            "create_internet_gateway":True,
            "enable_dns_hostnames":True,
            "enable_dns_support":True,
        }
        , instance_type="t3.small"
        , spot_types=[
            "t3.small"
            ,"t4g.small"
        ]
        , min_capacity=1
        , max_capacity=2
        , desired_capacity=1
        , domain_name="taloni.link"
        , record_name="test"
        , data_path="../data"
    )
    return ecs_props