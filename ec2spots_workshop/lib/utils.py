# AMI linux
import boto3        
import aws_cdk as core 
from operator import itemgetter
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
)

import os
import logging
from requests import get

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)


def _get_latest_amnz_ami():
    amnz_linux = ec2.MachineImage.latest_amazon_linux2(
        edition=ec2.AmazonLinuxEdition.STANDARD,
        virtualization=ec2.AmazonLinuxVirt.HVM,
        storage=ec2.AmazonLinuxStorage.GENERAL_PURPOSE
    )
    return amnz_linux

def _describe_ami(pattern: dict):
    ec2_client = boto3.client('ec2') 
    images = ec2_client.describe_images(
            Filters=[
                {
                    'Name': 'architecture',
                    'Values': [
                        pattern.get("architecture"),
                    ]
                },{
                    'Name': 'name',
                    'Values': [
                        pattern.get("name") ,
                    ]
                }
            ],
            Owners=[
                pattern.get("owner"),
            ],
        )
    image_details = sorted(images['Images'],key=itemgetter('CreationDate'),reverse=True)
    image_details[0]['ImageId']
    return image_details[0]['ImageId']

def get_latest_linux_ami_from_aws(pattern: dict, region: str) -> str:
    log.info(f"Getting latest linux AMI from AWS")
    _latest_image = None
    if pattern.get("owner") == "amazon":
        _latest_image = _get_latest_amnz_ami()
        log.debug(f"the linux AMI will be {_latest_image}")
    else:
        # Get latest image from AWS
        # aws ec2 describe-images --filters Name=owner-id,Values=777548758970 --query 'sort_by(Images, &CreationDate)[].Name' --region us-west-1 | jq '.[1]'
        # Sort on Creation date Desc
        try:
            ami_id = _describe_ami(pattern)
            _latest_image = ec2.MachineImage.generic_linux({
                region : ami_id      
            })
        except Exception as e:
            log.error(" Didn't find a image for ASG")
            log.error(e)
            raise e
        log.info(f"Linux: {ami_id}")
    # end if 
    return _latest_image

def add_tags(stacks: list, tags: map):
    for stack in stacks:
        for key, value in tags.items():
            core.Tags.of(stack).add(
                key, value
            )

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

def get_my_external_ip():
    ip = get('https://api.ipify.org').content.decode('utf8')
    return f"{ip}/32"