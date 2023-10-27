import typing
from aws_cdk import (
    # Duration,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sagemaker as sagemaker
)

from functions.utils import log

from constructs import Construct
from .sagemaker_lib import (
    NotebookLabProps,
    NotebookLab,
    Storage,
    BaseInfra,
    StepFunction
)

class SageMakerLab(Stack):

    def __init__(self, scope: Construct, construct_id: str,
                 cidr_block: str,
                 prefix_name: str,
                **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._base_infra = BaseInfra(
            self, "VPC",
            cidr_block=cidr_block,
            region=self.region,
            account=self.account    
        )

        vpc_id = self._base_infra.vpc.vpc_id
        sg_id = self._base_infra.asg_sg.security_group_id
        subnet_ids = [subnet.subnet_id for subnet in self._base_infra.vpc.private_subnets]

        props = NotebookLabProps(
            vpc_id = vpc_id,
            sg_id  = sg_id,
            subnet_ids = subnet_ids,
            log    = log,
            prefix_name= prefix_name
        )

        self._notebook = NotebookLab(
            self, "NotebookLab",
            props=props
        )

        self._step_function = StepFunction(
            self, "StepFunction"
        )

class SagemakerStorage(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 prefix_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._storage = Storage(
            self, "S3Storage",
            prefix_name=prefix_name
        )
