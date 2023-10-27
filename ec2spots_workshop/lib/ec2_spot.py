import aws_cdk as core
from aws_cdk import (
    Stack,
    aws_s3 as s3, 
    aws_ec2 as ec2, 
    aws_kms as kms, 
    aws_iam as iam,
    aws_autoscaling as asg,
    custom_resources as cr, 
    aws_s3_assets as Asset
)

from .utils import get_latest_linux_ami_from_aws

from constructs import Construct
from dataclasses import dataclass

import os
import time
import logging
import boto3

from operator import itemgetter
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

from .utils import get_my_external_ip


@dataclass
class EC2Props:
    ec2_type: str
    vpc: ec2.Vpc
    env: core.Environment
    prefix: str
    ami_image: str
    
public_ip_addresses = [
    get_my_external_ip()
]


class EC2Spot(Construct):
    @property
    def asg(self):
        return self._asg

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props: EC2Props,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = props.prefix
        self._vpc = props.vpc
        self._latest_image = props.ami_image        
        
        # Instance Role and SSM Manager Policy
        self._instance_role = iam.Role(
            self, f"{self._prefix.upper()}-InstanceSSM-IAM-Role",
            role_name=f"{self._prefix}-instance-role-ssm-policy",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        self._instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore")
        )

        # Create Security Group for instance
        self._sg_instance = ec2.SecurityGroup(
            self, f"{self._prefix.upper()}-SecurityGroup",
            vpc=self._vpc,
            allow_all_outbound=True,
            security_group_name=f"{self._prefix}-instance-ssm-sg"
        )


        for ip_address in public_ip_addresses:
            self._sg_instance.add_ingress_rule(
                peer=ec2.Peer.ipv4(ip_address),
                connection=ec2.Port.all_tcp()
            )

        # EC2 InstanceIMachineImage
        # instance = ec2.Instance(
        #     self, "BaseInstance",
        #     instance_name=f"{self._prefix}-instance-ssm",
        #     instance_type=ec2.InstanceType(props.ec2_type),
        #     role=instance_role,
        #     vpc=vpc,
        #     security_group=sg_instance,
        #     machine_image=latest_image,
        #     vpc_subnets=ec2.SubnetSelection(
        #         subnet_type=ec2.SubnetType.PUBLIC
        #     )
        # )

        # ASG + Spot
        
        workshop_asg_template = ec2.LaunchTemplate(
            self,
            id=f"{self._prefix}-spot-template",
            machine_image=self._latest_image,
            security_group=self._sg_instance,
            role=self._instance_role,
            instance_type=ec2.InstanceType(props.ec2_type)
        )
        
        
        # issue:
        # | CREATE_FAILED        | AWS::AutoScaling::AutoScalingGroup    | workshopec2spotstackWorkShopASG46A7BD41
        # Resource handler returned message: "SpotInstancePools option is only available with the lowest-price allocation strategy. 
        # (Service: AutoScaling, Status Code: 400, Request ID: c7869254-96e9-41d6-aa63-968f014eece1)"
        # (RequestToken: 1234-5678-...., HandlerErrorCode: InvalidRequest)
        # Solution: spot_instance_pools must be explicitly set to 0 when spot_allocation_strategy is set to anything other than lowest-price
        # "SpotInstancePools option is only available with the lowest-price allocation strategy
        
        self._asg = asg.AutoScalingGroup(
            self, f"{self._prefix.upper()}-ASG-Spots",
            vpc = self._vpc,
            auto_scaling_group_name=f"{self._prefix}-asg-spots",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            # Setting 'instanceType' must not be set when 'launchTemplate' or 'mixedInstancesPolicy' is set
            # instance_type=ec2.InstanceType(props.ec2_type),
            # Setting 'machineImage' must not be set when 'launchTemplate' or 'mixedInstancesPolicy' is set
            # machine_image=self._latest_image,
            min_capacity=0,
            max_capacity=2,
            # desired_capacity=1, # https://github.com/aws/aws-cdk/issues/5215
            # Setting 'securityGroup' must not be set when 'launchTemplate' or 'mixedInstancesPolicy' is set
            # security_group=self._sg_instance,
            # Setting 'role' must not be set when 'launchTemplate' or 'mixedInstancesPolicy' is set
            # role=self._instance_role,
            mixed_instances_policy=asg.MixedInstancesPolicy(
                instances_distribution=asg.InstancesDistribution(
                    on_demand_percentage_above_base_capacity=0,
                    on_demand_base_capacity=0,
                    spot_allocation_strategy = asg.SpotAllocationStrategy.PRICE_CAPACITY_OPTIMIZED,
                    # on_demand_allocation_strategy=,
                    # spot_instance_pools=0,
                ),
                launch_template=workshop_asg_template,
                launch_template_overrides=[
                    asg.LaunchTemplateOverrides(instance_type=ec2.InstanceType("t3.small")),
                    asg.LaunchTemplateOverrides(instance_type=ec2.InstanceType("t4g.small")),
                ]
            )
        )


        # Script in S3 as Asset
        asset = Asset.Asset(
            self, "Asset",
            path=os.path.join(dirname, "../scripts/configure.sh")
        )

        local_path = self._asg.user_data.add_s3_download_command(
            bucket=asset.bucket,
            bucket_key=asset.s3_object_key
        )

        # User data executes scripts from s3
        self._asg.user_data.add_execute_file_command(
            file_path=local_path
        )

        asset.grant_read(self._asg.role)
