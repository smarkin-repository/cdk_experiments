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
from constructs import Construct
from dataclasses import dataclass
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


@dataclass
class WebProps:
    prefix: str
    vpc: ec2.Vpc=None
    spot_types: List[str]=None
    instance_type: str=None
    min_capacity: int=0
    max_capacity: int=1
    desired_capacity: int=0
    ami_image: str=None
    domain_name: str=None
    record_name: str=None

class WebAsg(Construct):

    @property 
    def asg(self):
        return self._asg
    
    @property
    def instance_role(self):
        return self._instance_role
    
    @property
    def securety_group(self):
        return self._sg_instance
    
    @property
    def instance_profile(self):
        return self._instance_profile
    
    @property
    def launch_template(self):
        return self._launch_template
    
    @property
    def props(self):
        return self._props
    
    def _create_instance_role(self):
        """
        Instance Role and SSM Manager Policy
        """
        instance_role = iam.Role(
            self, f"{self._prefix.upper()}-InstanceSSM",
            role_name=f"{self._prefix}-instance-role-ssm-policy",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )
        instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore")
        )
        # read Policy Document from a json file
        policy_document = iam.PolicyDocument.from_json(
            json.load(open(os.path.join(dirname, "../data/policy", "ec2_policy.json")))
        )
        policy = iam.Policy(
            self, f"{self._prefix.upper()}-EC2-Policy",
            document=policy_document
        )
        # manager_policy
        # Attach Policy Document to Instance Role
        instance_role.attach_inline_policy(policy)
        
        # instance_role.
        return instance_role

    def _create_securety_group(self, vpc, port, allow_ip_addresses):
        sg_instance = ec2.SecurityGroup(
            self, f"{self._prefix.upper()}-SecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name=f"{self._prefix}-instance-ssm-sg"
        )


        for ip_address in allow_ip_addresses:
            sg_instance.add_ingress_rule(
                peer=ec2.Peer.ipv4(ip_address),
                connection=ec2.Port.tcp(port)
            )
        return sg_instance
    
    def _create_instance_profile(self, iam_roles: list):
        instance_profile = iam.CfnInstanceProfile(
            self, f"{self._prefix.upper()}-InstanceProfile",
            instance_profile_name=f"{self._prefix}-instance-profile-ssm-policy",
            roles=iam_roles
        )
        return instance_profile

    def _create_asg_template(
            self, 
            iam_role, 
            # instance_profile, 
            securety_group, 
            instance_type, 
            ami_image):
        return ec2.LaunchTemplate(
            self, f"{self._prefix}-spot-template",
            launch_template_name=f"{self._prefix}-launch-template-spots",
            machine_image=ami_image,
            security_group=securety_group,
            instance_type=ec2.InstanceType(instance_type),
            # instance_profile=instance_profile,
            role=iam_role,
        )
        
    def _create_mixed_instance_policy(self, asg_template, instance_types: list):
        """
            Spot instance only
        """
        return asg.MixedInstancesPolicy(
                instances_distribution=asg.InstancesDistribution(
                    on_demand_percentage_above_base_capacity=0,
                    on_demand_base_capacity=0,
                    spot_allocation_strategy = asg.SpotAllocationStrategy.PRICE_CAPACITY_OPTIMIZED,
                    # on_demand_allocation_strategy=,
                    # spot_instance_pools=0,
                ),
                launch_template=asg_template,
                launch_template_overrides=[
                    asg.LaunchTemplateOverrides(instance_type=ec2.InstanceType(name)) for name in instance_types
                ]
            )
    
    def _get_user_data(self, full_name: str):
        with open(os.path.join(dirname, full_name), 'r') as f:
            user_data = f.read()
        return ec2.UserData.custom(user_data)

    # def _asset_user_data(self, asg):
    #     # Script in S3 as Asset
    #     asset = Asset.Asset(
    #         self, f"{self._prefix}-asset",
    #         path=os.path.join(dirname, "../scripts/user_data.sh")
    #     )

    #     local_path = asg.user_data.add_s3_download_command(
    #         bucket=asset.bucket,
    #         bucket_key=asset.s3_object_key
    #     )

    #     # User data executes scripts from s3
    #     asg.user_data.add_execute_file_command(
    #         file_path=local_path
    #     )

    #     asset.grant_read(self._instance_role)
        # return asset

    
    def _asset_user_data(self, asg, script_paths: List[str]):
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
            asset.grant_read(self._instance_role)

        return assets
    
    def _create_asg(
            self, props: WebProps,
            launch_template,
            mixed_instances_policy,
            securety_group
        ):
        return asg.AutoScalingGroup(
            self, f"{self._prefix.upper()}-ASG-Web-App",
            auto_scaling_group_name=f"{self._prefix}-asg-web-app",
            vpc=props.vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            ),
            min_capacity=props.min_capacity,
            max_capacity=props.max_capacity,
            desired_capacity=props.desired_capacity,
            mixed_instances_policy=mixed_instances_policy,
        )
        
    def asset_user_data(self, data_path: str):
        script_paths=[]
        script_paths.append(
            os.path.join(dirname, f"{data_path}/user_data.sh"))
        return self._asset_user_data(self._asg, script_paths)
    
    def create_asg(self, props: WebProps=None):
        if props is None:
            props = self.props

        self._instance_role = self._create_instance_role()
        self._create_instance_profile = self._create_instance_profile([self._instance_role.role_name])
        self._sg_instance = self._create_securety_group(
            props.vpc, port=8080, allow_ip_addresses=[get_my_external_ip(), props.vpc.vpc_cidr_block])
        self._launch_template = self._create_asg_template(
            iam_role=self._instance_role
            # , instance_profile=self._create_instance_profile
            , securety_group=self._sg_instance
            , instance_type=props.instance_type
            , ami_image=props.ami_image
        )
        self._mixed_instances_policy = self._create_mixed_instance_policy(
            self._launch_template, props.spot_types)
        self._asg = self._create_asg(
            props,
            mixed_instances_policy=self._mixed_instances_policy,
            launch_template=self._launch_template,
            securety_group=self._sg_instance
        )

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props: WebProps,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = props.prefix
        self._props = props

        