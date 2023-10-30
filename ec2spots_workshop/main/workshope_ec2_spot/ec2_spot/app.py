#!/usr/bin/env python3
import os
import sys
import logging
import aws_cdk as core

# include python libraries from custum path by sys lib
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../ec2spots_workshop"))

from lib import ( 
    utils
    , EC2Props
    , EnvProps
    , WorkshopEC2SpotStack
    , TTLProps
    , ttl_termination_stack_factory
)


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


stacks = []
env = utils.get_current_env()
tags = {
    "Region" : env.region,
    "Owner" : "smarkin",
    "Environment" : "dev",
    "Role": "workshop",
    "Type": "cdk"
}

app = core.App()


@dataclass
class EnvProps:
    cidr_block: str
    prefix: str
    env: core.Environment
    propertis: Dict


# create and fill EnvPro
env_props = EnvProps(
    env=env,
    prefix="workshop",
    cidr_block="172.30.0.0/24",
    propertis={
        "create_internet_gateway":True,
        "enable_dns_hostnames":True,
        "enable_dns_support":True,
    }
)

ami_image = utils.get_latest_linux_ami_from_aws(
    region=env.region
    , pattern={
        "owner" : "amazon",
        "architecture" : "x86_64",
        "name" : "amzn2-ami-hvm-*"
    }
)

# create EC2SpotStack

test_stack = WorkshopEC2SpotStack(
    app, "WorkShopEc2SpotStack", 
    env_props=env_props, 
    ec2_type="t3.small",
    ami_image=ami_image,
)

stacks.append(test_stack)

# create and fill TTLProps
ttl_props = TTLProps(
    ttl = 120,
    prefix_name = f"{env_props.prefix}-ttl",
    account = env.account,
    region = env.region,
    stack_names = []
)

ttl_stack = ttl_termination_stack_factory(
    app, "WorkshopTTL", 
    ttl_props=ttl_props,
    stacks=stacks
)

ttl_stack.add_dependency(test_stack)
stacks.append(ttl_stack)

utils.add_tags(stacks, tags)
app.synth()

