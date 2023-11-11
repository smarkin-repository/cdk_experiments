#!/usr/bin/env python3
import os

import aws_cdk as cdk
import logging
import base_account_setup as app_stacks

# Default settings for loggin
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


stacks = []
prefix_name = "base"
tags = {
    "Owner" : "smarkin",
    "Type" : "CDK",
    "Project" : "BaseEnv",
    "CDK" : "True"
}

app = cdk.App()

try:
    env=cdk.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"])
    )
except KeyError:
    log.error("Try to run 'aws sso login' to refresh session")
    raise

log.info(f"""
         Hello! Start to work to create Base  Account Environment 
         - S3 Storage
         - ECR Repository

         You use follow enviornment values:
         - CDK_DEPLOY_ACCOUNT: {env.account}
         - CDK_DEPLOY_REGION: {env.region}
         
         """)

def add_tags(stacks: list, tags: dict):
    for stack in stacks:
        for key, value in tags.items():
            # cdk.Tag(stack, key, value)
            cdk.Tags.of(stack).add(key, value)

ecr_stack = app_stacks.ECR(app, "EcrStack", prefix_name=prefix_name, env=env)
stacks.append(ecr_stack)

s3_stack = app_stacks.Storage(app, "StorageStack", prefix_name=prefix_name, env=env)
stacks.append(s3_stack)

add_tags(stacks, tags)
   
app.synth()
