#!/usr/bin/env python3
import os
import sys
import logging
import aws_cdk as core

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../ec2spots_workshop"))

from lib import ( 
    EnvProps
    , WebProps
    , WorkshopWebAsgStack
    , ttl_termination_stack_factory
    , TTLProps
    , utils
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

# create and fill EnvPro
env_props = EnvProps(
    env=env, # It doen't need any more
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

web_props = WebProps(
    prefix="workshop"
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
)

test_stack = WorkshopWebAsgStack(
    app, f"{web_props.prefix.upper()}-WebASGStack"
    , env_props=env_props 
    , props=web_props
    , env = env
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
    app, "WorkShopTTL", 
    ttl_props=ttl_props,
    stacks=stacks
)
ttl_stack.add_dependency(test_stack)
stacks.append(ttl_stack)

utils.add_tags(stacks, tags)
app.synth()

