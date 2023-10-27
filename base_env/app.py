#!/usr/bin/env python3
import os

import aws_cdk as cdk
import logging
from base_env.base_kms_stack import BaseKmsStack

# Default settings for loggin
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


stacks = []
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


# TODO Attach notebook
# user CodeCommite and attach to SageMaker.
# cdk will be create repo with notebooks
# https://docs.aws.amazon.com/sagemaker/latest/dg/nbi-git-resource.html
# TODO Model Training  Jobs
# https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.aws_stepfunctions_tasks/SageMakerCreateTrainingJob.html
# TODO Model Creation

# For more information, see https://docs.aws.amazon.com/cdk/latest/guide/environments.html
# TODO add timeline/lifecycle for stacks
# TODO add Algorithms 

log.info(f"""
         Hello! Start to work to create Base Environment 
         - VPC
         - KMS

         You use follow enviornment values:
         - CDK_DEPLOY_ACCOUNT: {env.account}
         - CDK_DEPLOY_REGION: {env.region}
         
         """)

def add_tags(stacks: list, tags: dict):
    for stack in stacks:
        for key, value in tags.items():
            # cdk.Tag(stack, key, value)
            cdk.Tags.of(stack).add(key, value)

base_kms_stack = BaseKmsStack(app, "BaseKmsStack", env=env)
stacks.append(base_kms_stack)

add_tags(stacks, tags)
   
app.synth()
