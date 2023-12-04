#!/usr/bin/env python3
import os
import sys
import logging
import aws_cdk as core

sys.path.append(os.path.join(os.path.dirname(__file__), "../../../../ec2spots_workshop"))

from lib import ( 
    ECSProps
    , EnvProps
    , ClusterProps
    , WorkshopECSStack
    , WorkshopEnvStask
    , WorkshopServiceStack
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
    , env_props=EnvProps(
        cidr_block="172.30.0.0/24"
        , endpoints = [
                "ecs",
                "ecs-agent",
                "ssm",
                "ecr.dkr"
            ]
        , max_avz=2
        , endpoint_subnets=core.aws_ec2.SubnetSelection(subnet_type=core.aws_ec2.SubnetType.PRIVATE_WITH_EGRESS)
        , propertis={
            "create_internet_gateway":True,
            "enable_dns_hostnames":True,
            "enable_dns_support":True,
        }
        , alb_internet_facing=True
        , domain_name="taloni.link"
        , hosted_zone_id="Z0764436UNSJQPH92RK7"
        , record_name="test"
    )
    , cluster_props=ClusterProps(
        subnets = core.aws_ec2.SubnetSelection(subnet_type=core.aws_ec2.SubnetType.PRIVATE_WITH_EGRESS)
        , instance_type="t3.small"
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
        , data_path="../../../data/scripts"
    )
)


env_stack = WorkshopEnvStask(
    app, f"{prefix.capitalize()}-Env-Stack"
    , prefix=prefix 
    , props=ecs_props.env_props
    , env=env
)
stacks.append(env_stack)

ecs_props.cluster_props.vpc = env_stack.vpc
ecs_props.cluster_props.alb = env_stack.alb
ecs_props.cluster_props.acm_cert = env_stack.acm_cert

ecs_stack = WorkshopECSStack(
    app, f"{prefix.capitalize()}-Ecs-Stack"
    , prefix=prefix 
    , props=ecs_props
    , env = env
)

ecs_stack.add_dependency(env_stack)
stacks.append(ecs_stack)

# provide propertices of ecs_stack as 
#  - asg
#  - cluster
#  - ecs 
#  - acm_cert
# to cluster_props

ecs_props.cluster_props.asg = ecs_stack.asg
ecs_props.cluster_props.cluster = ecs_stack.cluster
ecs_props.cluster_props.ecs = ecs_stack.ecs

service_stack = WorkshopServiceStack(
    app, f"{prefix.capitalize()}-Service-Stack"
    , prefix=prefix
    , props=ecs_props.cluster_props
    , env=env
)

# service_stack.add_dependency(ecs_stack)
stacks.append(service_stack)


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

stacks.append(ttl_stack)

utils.add_tags(stacks, tags)
app.synth()

