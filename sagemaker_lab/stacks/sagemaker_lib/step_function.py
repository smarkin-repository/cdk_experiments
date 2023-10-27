from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_sagemaker as sagemaker,
    aws_secretsmanager as secretsmanager,
)

import os
import yaml
from constructs import Construct

class StepFunction(Construct):
    
    def __init__(self, scope: Construct, construct_id: str, 
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        