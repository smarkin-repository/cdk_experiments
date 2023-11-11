from aws_cdk import (
    Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_s3 as s3,
)

from constructs import Construct

class Storage(Stack):
    
    @property
    def bucket(self) -> s3.Bucket:
        return self._s3_bucket

    def __init__(self, scope: Construct, construct_id: str, 
                 prefix_name: str, 
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 bucket 
        self._s3_bucket = s3.Bucket(
            self, f"{prefix_name.capitalize()}S3Bucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            # encryption=s3.BucketEncryption.KMS_MANAGED,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            # delete old objects more then 180 days
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(180),
                    enabled=True,
                    # transitions=[
                    #     s3.Transition(
                    #         storage_class=s3.StorageClass.GLACIER,
                    #         transition_after=Duration.days(180)
                    #     )
                    # ]
                )  # 180 days
            ],
            bucket_name=f"{prefix_name}-s3-storage"
        )
        CfnOutput(self,f"{prefix_name.capitalize()}BucketName", value=self._s3_bucket.bucket_name)

