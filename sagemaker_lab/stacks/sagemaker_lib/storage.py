import typing
from aws_cdk import (
    # Duration,
    RemovalPolicy,
    CfnOutput,
    Stack,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_s3 as s3,
    aws_sagemaker as sagemaker
)

from constructs import Construct
from .props import NotebookLabProps



class Storage(Construct):
    
    @property
    def bucket(self) -> s3.Bucket:
        return self._s3_sm_bucket

    def __init__(self, scope: Construct, construct_id: str, 
                 prefix_name: str, 
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket 
        self._s3_sm_bucket = s3.Bucket(
            self, "BucketSMlab",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # encryption=s3.BucketEncryption.KMS_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            # lifecycle_rules=[]
            bucket_name=f"{prefix_name}-storage"
        )
        
        CfnOutput(self,"S3 bucket name", value=self._s3_sm_bucket.bucket_name)

