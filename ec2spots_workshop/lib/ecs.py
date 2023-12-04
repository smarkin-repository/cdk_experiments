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
# from .props import ClusterProps
from .utils import get_my_external_ip, get_latest_linux_ami_from_aws
from .aws_framework import AWSFramework

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
    def _get_vpc_by_name(self):
        return ec2.Vpc.from_lookup(self, "VPC", vpc_name=self._vpc_name)
    
    def _get_vpc(self):
        return self._props.vpc
    
    def _get_subnets(self):
        return self._props.subnets
    
    def _prepare_data_paths(self, path, files) -> List:
        paths = []
        for file in files:
            paths.append("/".join([path,file]))
        return paths 
    
    def _get_name_id(self, name):
        return f"{self._prefix.capitalize()}-{name}"

    def _create_instance_profile(self, iam_roles: list):
        instance_profile = iam.CfnInstanceProfile(
            self, f"{self._prefix.upper()}-InstanceProfile",
            instance_profile_name=f"{self._prefix}-instance-profile-ssm-policy",
            roles=iam_roles
        )
        return instance_profile
    
    def _create_launch_template(self, securety_group, iam_role, instance_type, image=None, user_data=None):
        return ec2.LaunchTemplate(self, "ASG-LaunchTemplate",
            instance_type=instance_type,
            machine_image=image,
            role=iam_role,
            security_group=securety_group,
            require_imdsv2=True,
            user_data=user_data
        )

    def _user_data(self, instance_role, script_paths: List[str]):
        """
        Create an asset for each script in the list
        """
        # check exists directory with script_paths
        for script_path in script_paths:
            if not os.path.exists(script_path):
                raise ValueError(f"Script path {script_path} not found")
        
        # create assets and publish on s3 bucket
        assets = []
        for script_path in script_paths:
            asset = Asset.Asset(
                self, f"{self._prefix}-asset",
                path=script_path
            )
            assets.append(asset)

        # create class user_data aws_cdk.aws_ec2.UserData
        user_data = ec2.UserData.for_linux()

        # Add commands to execute scripts
        # Grant read permissions for all assets to the instance role
        for asset in assets:
            local_path = user_data.add_s3_download_command(
                bucket=asset.bucket,
                bucket_key=asset.s3_object_key
            )
            user_data.add_execute_file_command(
                file_path=local_path
            )
            asset.grant_read(instance_role)
        return user_data
    
    def _cretae_mixed_instances_policy(self, launch_template ):
        return asg.MixedInstancesPolicy(
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

    def _create_asg(
            self, auto_scaling_group_name, 
            vpc, 
            vpc_subnets,
            min_capacity=0,
            max_capacity=3,
            desired_capacity=1,
            new_instances_protected_from_scale_in=False,
            mixed_instances_policy=None, 
            launch_template=None, 
        ):
        _asg = asg.AutoScalingGroup(self, self._get_name_id(name="ASG"),
            vpc=vpc,
            auto_scaling_group_name=auto_scaling_group_name,
            vpc_subnets= vpc_subnets, # self._props.subnets,
            min_capacity=min_capacity,
            max_capacity=max_capacity,
            desired_capacity=desired_capacity,
            new_instances_protected_from_scale_in=new_instances_protected_from_scale_in,
            mixed_instances_policy=mixed_instances_policy,
            launch_template=launch_template
        )
        return _asg
    
    def _create_securety_group(self, vpc, ports, allow_ip_addresses):
        return self._frame_work.create_securety_group(
            id=self._get_name_id(name="ecs-sg"),
            name="instance-ecs-sg",
            description="Security group for ECS instances",
            ports=ports, #[80,443],
            vpc=vpc,
            allow_ip_addresses=allow_ip_addresses #[get_my_external_ip(), vpc.vpc_cidr_block] 
        )
    
    def _create_instance_role(self):
        return self._frame_work.create_instance_role(
            id=self._get_name_id(name="ecs-iam-role"),
            role_name="ecs-instance-iam-role",
            description="IAM role for ECS instances",
            name_services=[
                "ec2.amazonaws.com",
                "ecr.amazonaws.com",
            ],
            manage_policies=[
                "AmazonSSMManagedInstanceCore",
                "AmazonS3ReadOnlyAccess",
                "service-role/AmazonEC2ContainerServiceforEC2Role",
                "AmazonEC2ContainerRegistryReadOnly",
                "AmazonEC2FullAccess"
            ]
        )

    def create_asg_for_ecs(
            self,
            sg_ports=None, 
            instance_type=ec2.InstanceType("t3.media"), 
            image=ecs.EcsOptimizedImage.amazon_linux2(), 
            iam_role=None, 
            securety_group=None, 
            allow_ip_addresses=None,
            data_files: List=None
        ):
        vpc = self._get_vpc()
        vpc_subnets = self._get_subnets()

        data_paths = self._prepare_data_paths(
            path=self._props.data_path, files=data_files)

        securety_group = self._create_securety_group(vpc, sg_ports, allow_ip_addresses) if securety_group is None else securety_group
        role = self._create_instance_role() if iam_role is None else iam_role

        _user_data = self._user_data(role, data_paths)
        
        # FIXME For some resone Accests doesn't work well.
        launch_template = self._create_launch_template(
            securety_group, 
            iam_role=role, 
            instance_type=instance_type, 
            image=image,
            user_data=None#_user_data
        )
        mixed_instances_policy = self._cretae_mixed_instances_policy(
            launch_template=launch_template
        )

        _asg = self._create_asg(
            auto_scaling_group_name=f"{self._prefix}-ASG",
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            mixed_instances_policy=mixed_instances_policy
        )
        return _asg
    
    def create_cluster(self, autoscaling_group):
        _cluster = ecs.Cluster(
            self, f"{self._prefix.capitalize()}-Cluster", 
            cluster_name=f"{self._prefix.capitalize()}-App-Cluster",
            vpc=self._get_vpc())

        capacity_provider = ecs.AsgCapacityProvider(
            self, f"{self._prefix.capitalize()}-AsgCapacityProvider",
            auto_scaling_group=autoscaling_group,
            enable_managed_termination_protection=False,
            enable_managed_scaling=True
        )
        _cluster.add_asg_capacity_provider(capacity_provider)
        return _cluster
    
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

    def create_service(self, cluster, container_name, image):
        # Create Task Definition
        task = self._create_task_definition()

        # ecr_repo = ecr.Repository.from_repository_name("")
        # tag = "latest"
        # image = ecs.ContainerImage.from_ecr_repository(ecr_repo, tag)
        # public.ecr.aws/ecs-sample-image/amazon-ecs-sample:latest тоже ходит через интерент
        # надо отдельно тестировать доступ к ECR

        task.add_container(
            container_name, 
            image=image,
            # image=image,
            # environment={
            #     "ECS_CLUSTER": "Workshop-App-Cluster"
            # },
            memory_limit_mib=256,
            cpu=256,
            port_mappings=[ecs.PortMapping(container_port=80, host_port=80)]
        )
        # Create Service
        service = self._create_service(cluster, task, container_name)
        return service

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            prefix: str,
            props,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = prefix
        self._props = props
        self._frame_work = AWSFramework(self, f"{construct_id}-Framework" )


