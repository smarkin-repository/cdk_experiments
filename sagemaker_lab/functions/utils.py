import os
import logging
import aws_cdk as core
from requests import get
from constructs import Construct
from .ttl import (
    TTLProps,
    TTLStack,
)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)



def add_tags(stacks: list, tags: dict):
    for stack in stacks:
        for key, value in tags.items():
            core.Tags.of(stack).add(key, value)


def get_current_env() -> core.Environment:
    try:
        env=core.Environment(
            account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
            region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
        )
    except KeyError:
        log.error(" Try to run 'aws sso login' to refresh session!")
        raise
    return env

# Get My external IP address
def get_my_external_ip():
    ip = get('https://api.ipify.org').content.decode('utf8')
    return f"{ip}/32"


# return Stack with TTL termination stacks get as argumetns of the functions
def ttl_termination_stack_factory(
        scope: Construct, construct_id: str, 
        ttl_props: TTLProps,
        stacks: list
    ):
    # add all stacks names to ttl_props if it doesn't have terminition protection

    for stack in stacks:
        if stack.termination_protection is True:
            continue
        ttl_props.stack_names.append(stack.stack_name)
        log.info(f"Added stack {stack.stack_name} to TTL termination stack")
    
    log.info("Create TTL termination stack with follow props:")
    log.info(f"{ttl_props}")
    
    return TTLStack(
        scope=scope,
        construct_id=construct_id,
        props=ttl_props
    )
