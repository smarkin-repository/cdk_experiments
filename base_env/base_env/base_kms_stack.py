import os.path

from aws_cdk.aws_s3_assets import Asset
from constructs import Construct

from aws_cdk import (
    # Duration,
    CfnOutput,
    Stack,
    aws_kms as kms,
)

dirname = os.path.dirname(__file__)

class BaseKmsStack(Stack):

    @property
    def kms(self):
        return self._kms

    # @property
    # def alias(self):
    #     return self._alias

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._kms = kms.Key(
            self, "BaseKmsKey",
            description="base kms key",
            alias="base_kms_key"
        )

        # self._alias = kms.Alias(
        #     self, "Alias",
        #     alias_name="base_kms_key",
        #     target_key=self._kms
        # )

        CfnOutput(self, "BaseKmsName", value=self._kms.key_arn)
        # CfnOutput(self, "BaseKmsArn", value=self._alias.key_arn)
