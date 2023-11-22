#!/usr/bin/env python3
import os
import sys
import logging
import aws_cdk as core

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../ec2spots_workshop"))

from lib import ( 
    ECSProps
    , VPCProps
    , ClusterProps
    , R53Props
    , WorkshopECSStack
    , WorkshopEnvStask
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
prefix = "workshop"

ecs_props = ECSProps(
    env=env
    , vpc_props=VPCProps(
        cidr_block="172.30.0.0/24"
        , subnets=core.aws_ec2.SubnetSelection(subnet_type=core.aws_ec2.SubnetType.PRIVATE_WITH_EGRESS)
        , propertis={
            "create_internet_gateway":True,
            "enable_dns_hostnames":True,
            "enable_dns_support":True,
        }
    )
    , cluster_props=ClusterProps(
        instance_type="t3.small"
        , spot_types=[
            "t3.small"
            ,"t4g.small"
        ]
        , min_capacity=1
        , max_capacity=2
        , desired_capacity=1
        , ami_image=utils.get_latest_linux_ami_from_aws(
            region=env.region
            , pattern={
                "owner" : "amazon",
                "architecture" : "x86_64",
                "name" : "amzn2-ami-hvm-*"
            }
        )
        , data_path="../data/"
    )
    , r53_props=R53Props(
        domain_name="taloni.link"
        , record_name="test"
    )
)


env_stack = WorkshopEnvStask(
    app, f"{prefix.capitalize()}-Env-Stack"
    , prefix=prefix 
    , props=ecs_props.vpc_props
    , env=env
)
stacks.append(env_stack)

ecs_props.vpc_props.vpc = env_stack.vpc
ecs_props.vpc_props.alb_sg = env_stack.sg

ecs_stack = WorkshopECSStack(
    app, f"{prefix.capitalize()}-ECS-Stack"
    , prefix=prefix 
    , props=ecs_props
    , env = env
)
ecs_stack.add_dependency(env_stack)
stacks.append(ecs_stack)


# create and fill TTLProps
ttl_props = TTLProps(
    ttl = 120,
    prefix_name = f"{prefix}-ttl",
    stack_names = []
)

ttl_stack = ttl_termination_stack_factory(
    app, "WorkShopTTL", 
    ttl_props=ttl_props,
    stacks=stacks,
    env=env

)
ttl_stack.add_dependency(ecs_stack)
stacks.append(ttl_stack)

utils.add_tags(stacks, tags)
app.synth()

