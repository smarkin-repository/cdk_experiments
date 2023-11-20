import aws_cdk as core
from aws_cdk import (
    Stack,
    aws_ecr as ecr,
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
    
    def _create_launch_template(self, securety_group, iam_role, instance_type, image=None):
        return ec2.LaunchTemplate(self, "ASG-LaunchTemplate",
            instance_type=instance_type,
            machine_image=image,
            role=iam_role,
            security_group=securety_group,
            require_imdsv2=True
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
    def _create_task_definition(self, network_mode=ecs.NetworkMode.BRIDGE) -> ecs.Ec2TaskDefinition:
        """
            create a task definition for ECS cluster
        """
        task_definition = ecs.Ec2TaskDefinition(
            self, f"{self._prefix.capitalize()}-TaskDefinition",
            network_mode=network_mode
        )
        return task_definition

    def _create_service(self, cluster, task_definition, container_name):
        return ecs.Ec2Service(
            self, f"{self._prefix.capitalize()}-Service",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            # assign_public_ip=True,
            # cloud_map_options=ecs.CloudMapOptions(
            #     cloud_map_namespace=ecs.PrivateDnsNamespace(
            #         self, f"{self._prefix.capitalize()}-PrivateDnsNamespace",
            #         name=f"{self._prefix}-private-dns-namespace",
            #         vpc=cluster.vpc,
            #         description="Private DNS Namespace for ECS Cluster"
            #     ),
            #     name=container_name,
            #     cloud_map_service_type=ecs.CloudMapServiceType.HTTP
            # )
        )

    def _asset_user_data(self, asg, instance_role, script_paths: List[str]):
        """
        Create an asset for each script in the list
        """
        assets = []
        for script_path in script_paths:
            asset = Asset.Asset(
                self, f"{self._prefix}-asset",
                path=script_path
            )

        local_path = asg.user_data.add_s3_download_command(
            bucket=asset.bucket,
            bucket_key=asset.s3_object_key
        )

        assets.append(asset)

        # Add commands to execute downloaded scripts
        for asset in assets:
            asg.user_data.add_execute_file_command(
                file_path=local_path
            )

        # Grant read permissions for all assets to the instance role
        for asset in assets:
            asset.grant_read(instance_role)

        return assets

    def create_asg(self, vpc, iam_role=None, allow_ip_addresses=None):
        securety_group = self._create_securety_group(
            vpc=vpc,
            allow_cidr_blocks=[get_my_external_ip(), vpc.vpc_cidr_block] 
        )
        role = self._create_instance_role()
        launch_template = self._create_launch_template(
            securety_group, 
            iam_role=role, 
            instance_type=ec2.InstanceType("t3.media"), 
            image=ecs.EcsOptimizedImage.amazon_linux2()
        )
        _asg = asg.AutoScalingGroup(self, f"{self._prefix.capitalize}-ASG",
            vpc=vpc,
            auto_scaling_group_name=f"{self._prefix}-ecs-spots",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            min_capacity=0,
            max_capacity=3,
            desired_capacity=1,
            new_instances_protected_from_scale_in=False,
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
                    asg.LaunchTemplateOverrides(instance_type=ec2.InstanceType("t3.medium")),
                    asg.LaunchTemplateOverrides(instance_type=ec2.InstanceType("t4g.medium")),
                ]
            )
        )

        script_paths=[]
        script_paths.append(
            os.path.join(dirname, f"{self._props.data_path}/scripts/user_data_ecs.sh"))
        self._asset_user_data(_asg, role, script_paths)
        return _asg

    def create_cluster(self, vpc, autoscaling_group):
        _cluster = ecs.Cluster(self, f"{self._prefix.capitalize()}-Cluster", vpc=vpc)
    
        capacity_provider = ecs.AsgCapacityProvider(
            self, f"{self._prefix.capitalize()}-AsgCapacityProvider",
            auto_scaling_group=autoscaling_group,
            enable_managed_termination_protection=False,
            enable_managed_scaling=True
        )
        _cluster.add_asg_capacity_provider(capacity_provider)
        return _cluster
    
    def create_service(self, cluster, container_name):
        # Create Task Definition
        task = self._create_task_definition()

        # ecr_repo = ecr.Repository.from_repository_name("")
        # tag = "latest"
        # image = ecs.ContainerImage.from_ecr_repository(ecr_repo, tag)
        # public.ecr.aws/ecs-sample-image/amazon-ecs-sample:latest тоже ходит через интерент
        # надо отдельно тестировать доступ к ECR

        task.add_container(
            container_name, 
            image=ecs.ContainerImage.from_registry("public.ecr.aws/ecs-sample-image/amazon-ecs-sample:latest"),
            # image=image,
            memory_limit_mib=256,
            cpu=256,
            port_mappings=[ecs.PortMapping(container_port=80, host_port=8080)]
        )
        # Create Service
        return self._create_service(cluster, task, container_name)

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props: ECSProps,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = props.prefix
        self._props = props

        