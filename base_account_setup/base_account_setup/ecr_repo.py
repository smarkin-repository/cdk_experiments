import os.path
from constructs import Construct

from aws_cdk import (
    Duration,
    CfnOutput,
    Stack,
    RemovalPolicy,
    aws_ecr as ecr,
)

dirname = os.path.dirname(__file__)

class ECR(Stack):

    @property
    def ecr(self):
        return self._ecr

    def __init__(self, scope: Construct, construct_id: str, prefix_name: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # ECR repository
        self._ecr = ecr.Repository(
            self, f"{prefix_name.capitalize()}BaseECR",
            repository_name=f"{prefix_name}-repo",
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            image_scan_on_push=False,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                ecr.LifecycleRule(
                    description="Keep only the last 10 images",
                    # Life cycle rule must contain exactly one of 'maxImageAge' and 'maxImageCount'
                    max_image_count=10,
                    # max_image_age=Duration.days(180),
                    tag_prefix_list=["latest"],
                    rule_priority=1,
                )
            ]
        )

        CfnOutput(self, f"{prefix_name.capitalize()}RepoArn", value=self._ecr.repository_arn)
        CfnOutput(self, f"{prefix_name.capitalize()}RepoName", value=self._ecr.repository_name)
        CfnOutput(self, f"{prefix_name.capitalize()}RepoUri", value=self._ecr.repository_uri)
