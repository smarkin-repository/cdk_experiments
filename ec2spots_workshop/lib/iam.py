import aws_cdk as core
from aws_cdk import (
    aws_iam as iam
)


from constructs import Construct
from dataclasses import dataclass

import os
import logging


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

class IAM(Construct):

    def create_ssm_role(self, role_name):
        role = iam.Role(
            self, f"{self._prefix.upper()}-InstanceSSM-IAM-Role",
            role_name=f"{self._prefix}-{role_name}",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com")
        )

        role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMManagedInstanceCore")
        )
        return role
    
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            prefix: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = prefix

        
