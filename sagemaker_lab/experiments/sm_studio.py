from aws_cdk import (
    # Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sagemaker as sagemaker,
    cloudformation_include as cfn,
    aws_secretsmanager as secretsmanager
)

import typing as t

from constructs import Construct
from dataclasses import dataclass, field
import os.path as path

@dataclass
class SageMakerStudioProps:
    vpc: ec2.Vpc
    sg_id: str 
    instance_type: str = "ml.t3.medium"
    user_names: t.List[str] = field(default_factory=lambda: ["default-user"])
    jupyter_image: str = "jupyter-server-3"
    kernel_image: str  = "sagemaker-data-science-310-v1"

# TODO rewrite from here https://github.com/aws-samples/aws-cdk-native-sagemaker-studio/blob/main/cdk/cdk/sagemaker_studio_construct.py

class SageMakerStudio(Construct):

    @property
    def sg_studio(self):
        return self._domain_studio

    def __init__(self, scope: Construct, 
                 id: str, props: SageMakerStudioProps, **kwargs) -> None:
        super().__init__(scope, id)

        # Role for SageMakerStudio
        self._iam_role = iam.Role(
            self, "SageMakerStudioRole",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com"),
            role_name="SageMakerStudioRole",
            managed_policies=[
                iam.ManagedPolicy.from_managed_policy_arn(
                    self, "SagemakerFullAccess",
                    managed_policy_arn="arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
                )
            ])
        self._domain_name = "SageMakerLab"

        subnet_ids =[ subnet.subnet_id for subnet in props.vpc.public_subnets ]

        user_property = sagemaker.CfnDomain.UserSettingsProperty(
            execution_role=self._iam_role.role_arn,
            jupyter_server_app_settings=sagemaker.CfnDomain.JupyterServerAppSettingsProperty(
                default_resource_spec=sagemaker.CfnDomain.ResourceSpecProperty(
                    instance_type="system",
                    sage_maker_image_arn=f"arn:aws:sagemaker:us-east-1:081325390199:image/{props.jupyter_image}", # FIXME HARDCODE
                )
            ),
            kernel_gateway_app_settings = sagemaker.CfnDomain.KernelGatewayAppSettingsProperty(
                default_resource_spec=sagemaker.CfnDomain.ResourceSpecProperty(
                    instance_type=props.instance_type,
                    sage_maker_image_arn=f"arn:aws:sagemaker:us-east-1:081325390199:image/{props.kernel_image}", # FIXME HARDCODE
                )
            ),
            security_groups=[props.sg_id],
            sharing_settings=sagemaker.CfnDomain.SharingSettingsProperty(
                notebook_output_option="Disabled"
            )
        )

        self._domain_studio = sagemaker.CfnDomain(
            self, "SageMakerDomain",
            auth_mode="IAM",
            # auth_mode="SSO",
            default_user_settings=user_property,
            domain_name="SageMakerDomain1",
            subnet_ids=subnet_ids,
            vpc_id=props.vpc.vpc_id,
            app_network_access_type="PublicInternetOnly"
        )

        for user_name in props.user_names:
            sagemaker.CfnUserProfile(
                self, "SageMakerStudioProfile_" + user_name,
                domain_id=self._domain_studio.attr_domain_id,
                user_profile_name=user_name,
            )

        # Create a security group
        # self._sg = ec2.SecurityGroup(
        #     self, "SageMakerSecurityGroup",
        #     vpc=self.vpc,
        #     allow_all_outbound=True,
        #     description="Allow SageMaker Studio access")

        # Create SageMake Studion

        # self._domain_studio = cfn.CfnInclude(
        #     self, "SageMakerStudio", 
        #     template_file=path.join(
        #         path.dirname(path.abspath(__file__)),
        #         "templates/sagemaker-domain-template.yaml"
        #     ),
        #     parameters={
        #         "auth_mode" : "IAM",
        #         "domain_name" : self._domain_name,
        #         "subnet_ids" : subnet_ids,
        #         "vpc_id" : props.vpc.vpc_id,
        #         "default_execution_role_user" : self._iam_role.role_arn
        #     }
        # )
        
        # sagemaker_domain_id = self._domain_studio.attr_domain_id

        # # Add SageMaker users
        # user_name = "x-user"
        # self._studio_user = cfn.CfnInclude(
        #     self, "SageMakerStudioProfile",
        #     template_file=path.join(
        #         path.dirname(path.abspath(__file__)),
        #         "templates/sagemaker-user-template.yaml"
        #     ),
        #     parameters={
        #         "sagemaker_domain_id" : sagemaker_domain_id,
        #         "user_profile_name" : user_name
        #     },
        #     preserve_logical_ids=False
        # )
        # self._user_profile_id = self._studio_user.get_resource("SagemakerUser").get_att(
        #     'UserProfilArn'
        # ).to_string()



        
        
