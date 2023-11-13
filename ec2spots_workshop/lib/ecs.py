import aws_cdk as core
from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_s3 as s3, 
    aws_ecs_patterns as ecs_patterns, 
    aws_ec2 as ec2, 
    aws_iam as iam,
    aws_autoscaling as asg,
    custom_resources as cr, 
    aws_s3_assets as Asset
)
from constructs import Construct
from .props import ECSProps
from .utils import get_my_external_ip, get_latest_linux_ami_from_aws

import os
import time
import logging
import boto3

from operator import itemgetter
from typing import List, Dict
import json

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)


class ECS(Construct):

    @property
    def asg(self):
        return self._asg

    def _create_instance_role(self):
        # Instance Role and SSM Manager Policy
        instance_role = iam.Role(
            self, f"{self._prefix.upper()}-InstanceSSM-IAM-Role",
            role_name=f"{self._prefix}-instance-role-ssm-policy",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore")
        )
        return instance_role

    def _create_instance_profile(self, iam_roles: list):
        instance_profile = iam.CfnInstanceProfile(
            self, f"{self._prefix.upper()}-InstanceProfile",
            instance_profile_name=f"{self._prefix}-instance-profile-ssm-policy",
            roles=iam_roles
        )
        return instance_profile
    
    def _create_launch_template(self):
        pass

    def create_cluster(self, prefix, vpc, allow_ip_addresses):
        cluster = ecs.Cluster(self, "Cluster", vpc=vpc)

        # Create Security Group for instance
        sg = ec2.SecurityGroup(
            self, f"{self._prefix.upper()}-SecurityGroup",
            vpc=self._vpc,
            allow_all_outbound=True,
            security_group_name=f"{self._prefix}-instance-ssm-sg"
        )

        for ip_address in allow_ip_addresses:
            sg.add_ingress_rule(
                peer=ec2.Peer.ipv4(ip_address),
                connection=ec2.Port.all_tcp()
            )

        launch_template = ec2.LaunchTemplate(self, "ASG-LaunchTemplate",
            instance_type=ec2.InstanceType("t3.small"),
            machine_image=ecs.EcsOptimizedImage.amazon_linux2(),
            instance_profile=self._create_instance_profile(iam_roles=self._create_instance_role()),
            security_group=sg,
        )

        self._asg = asg.AutoScalingGroup(self, "ASG",
            vpc=vpc,
            launch_template=launch_template,
            auto_scaling_group_name=f"{self._prefix}-ecs-spots",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            min_capacity=1,
            max_capacity=3,
            desired_capacity=1,
            mixed_instances_policy=asg.MixedInstancesPolicy(
                instances_distribution=asg.InstancesDistribution(
                    on_demand_percentage_above_base_capacity=0,
                    on_demand_base_capacity=0,
                    spot_allocation_strategy = asg.SpotAllocationStrategy.PRICE_CAPACITY_OPTIMIZED,
                    # on_demand_allocation_strategy=,
                    # spot_instance_pools=0,
                ),
                launch_template=launch_template,
                launch_template_overrides=[
                    asg.LaunchTemplateOverrides(instance_type=ec2.InstanceType("t3.small")),
                    asg.LaunchTemplateOverrides(instance_type=ec2.InstanceType("t4g.small")),
                ]
            )
        )


        capacity_provider = ecs.AsgCapacityProvider(self, "AsgCapacityProvider",
            auto_scaling_group=self._asg
        )
        cluster.add_asg_capacity_provider(capacity_provider)

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props: ECSProps,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = props.prefix
        self._props = props

        