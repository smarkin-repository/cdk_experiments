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
    
    def _create_launch_template(self, securety_group, iam_role, image=None):
        return ec2.LaunchTemplate(self, "ASG-LaunchTemplate",
            instance_type=ec2.InstanceType("t3.small"),
            machine_image=image,
            role=iam_role,
            security_group=securety_group,
        )
    
    def _create_securety_group(self, vpc, allow_cidr_blocks ):
        sg = ec2.SecurityGroup(
            self, f"{self._prefix.upper()}-SecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name=f"{self._prefix}-instance-ssm-sg"
        )
        for ip_address in allow_cidr_blocks:
            sg.add_ingress_rule(
                peer=ec2.Peer.ipv4(ip_address),
                connection=ec2.Port.all_tcp()
            )

    def create_asg(self, vpc, iam_role=None, allow_ip_addresses=None):
        securety_group = self._create_securety_group(
            vpc=vpc,
            allow_cidr_blocks=[get_my_external_ip(), vpc.vpc_cidr_block] 
        )
        role = self._create_instance_role()
        launch_template = self._create_launch_template(
            securety_group, iam_role=role, image=ecs.EcsOptimizedImage.amazon_linux2())
        return asg.AutoScalingGroup(self, f"{self._prefix.capitalize}-ASG",
            vpc=vpc,
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

    def create_cluster(self, vpc, autoscaling_group):
        _cluster = ecs.Cluster(self, f"{self._prefix.capitalize()}-Cluster", vpc=vpc)
    
        capacity_provider = ecs.AsgCapacityProvider(
            self, f"{self._prefix.capitalize()}-AsgCapacityProvider",
            auto_scaling_group=autoscaling_group
        )
        _cluster.add_asg_capacity_provider(capacity_provider)
        return _cluster
    
    def create_service(self, cluster, container_name):
        # Create Task Definition
        task = ecs._create_task_definition()
        container = ecs.add_container_definition(task)
        # Create Service
        service = ecs.create_service(cluster, task)

# // Create Task Definition
# const taskDefinition = new ecs.Ec2TaskDefinition(stack, 'TaskDef');
# const container = taskDefinition.addContainer('web', {
#   image: ecs.ContainerImage.fromRegistry("amazon/amazon-ecs-sample"),
#   memoryLimitMiB: 256,
# });

# container.addPortMappings({
#   containerPort: 80,
#   hostPort: 8080,
#   protocol: ecs.Protocol.TCP
# });

# // Create Service
# const service = new ecs.Ec2Service(stack, "Service", {
#   cluster,
#   taskDefinition,
# });

        # return ecs.Ec2Service(
        #     self, f"{self._prefix.capitalize()}-Service",
        #     cluster=cluster,
        #     task_definition=task_definition,
        #     desired_count=1,
        #     assign_public_ip=True,
        #     cloud_map_options=ecs.CloudMapOptions(
        #         cloud_map_namespace=ecs.PrivateDnsNamespace(
        #             self, f"{self._prefix.capitalize()}-PrivateDnsNamespace",
        #             name=f"{self._prefix}-private-dns-namespace",
        #             vpc=cluster.vpc,
        #             description="Private DNS Namespace for ECS Cluster"
        #         ),
        #         name=container_name,
        #         cloud_map_service_type=ecs.CloudMapServiceType.HTTP
        #     )
        # )

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props: ECSProps,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = props.prefix
        self._props = props

        