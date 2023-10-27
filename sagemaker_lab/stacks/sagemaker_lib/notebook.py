import typing
from aws_cdk import (
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_sagemaker as sagemaker,
    aws_secretsmanager as secretsmanager,
    SecretValue
)

import os
import subprocess
import yaml
from constructs import Construct
from .props import NotebookLabProps 

def sops_decode(file: str, data_type: str, kms_key_arn: str=None) -> dict:
    sops_args=[
        "sops" , "-d", 
        "--input-type", data_type ,"--output-type", data_type,
        "--verbose",  file
    ]
    print(sops_args)
    result = subprocess.run(sops_args, stdout=subprocess.PIPE)
    secrets = yaml.safe_load(result.stdout)
    return secrets

class NotebookLab(Construct):

    @property
    def notebook_instance(self):
        return self._notebook_instance
    
    def __init__(self, scope: Construct, construct_id: str, 
                 props: NotebookLabProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # IAM Role access to s3 bucket for notebook
        self._sm_iam_role = iam.Role(
            self, "notebook-lab-access-role",
            role_name=f"{props.prefix_name}-notebook-role",
            assumed_by=iam.ServicePrincipal("sagemaker.amazonaws.com")
        )

        _statement_s3 = iam.PolicyStatement(
            actions=[
                's3:*',
            ],
            resources=[
                '*',
            ]
        )

        _statement_repo = iam.PolicyStatement(
            actions=[
                'codecommit:GitPull',
                'codecommit:GitPush'
            ],
            resources=[
                '*',
            ]
        )


        self._sm_role_policy = iam.Policy(
            self, "notebook-lab-access-policy",
            policy_name=f"{props.prefix_name}-notebook-access-policy",
            statements=[_statement_s3, _statement_repo]
        )
        self._sm_role_policy.attach_to_role(self._sm_iam_role)

        subnet_ids = props.subnet_ids

        secrets = sops_decode(
            "".join([os.path.dirname(__file__),"/../../../configs/dev/","secrets.yaml.enc"])
            , "yaml" 
            , "arn:aws:kms:us-east-1:500480925365:alias/base_kms_key" 
        )
        github_secret = secretsmanager.Secret(
            self, "GitHubSecret",
            description="GitHub Secret",
            secret_name="AWSCURRENT",
            secret_object_value={
                "username" : SecretValue(secrets.get("github").get("username")),
                "password" : SecretValue(secrets.get("github").get("password"))
            }
        )

        # # Grant permission to use the secret to a role
        github_secret.grant_read(
            self._sm_iam_role
        )

        repository = sagemaker.CfnCodeRepository(
            self, "NoteBookRepo",
            git_config=sagemaker.CfnCodeRepository.GitConfigProperty(
                repository_url="https://github.com/smarkin-repository/notebooks.git",
                branch="main",
                secret_arn=github_secret.secret_arn,
            ),
            code_repository_name=f"{props.prefix_name}-notebooks",
        )

        # SageMaker
        sg_name_id = f"{props.prefix_name}-sage-maker-lab-ml-t2"
        self._notebook_instance = sagemaker.CfnNotebookInstance(
            self, sg_name_id,
            instance_type="ml.t2.medium",
            role_arn=self._sm_iam_role.role_arn,
            subnet_id=subnet_ids[0],
            security_group_ids=[props.sg_id],
            volume_size_in_gb=5,
            notebook_instance_name=sg_name_id,
            default_code_repository=repository.code_repository_name,
            # additional_code_repositories="",
        ) 

        # CfnOutput(self,"notebook_instance", value=self._notebook_instance)
        # https://docs.aws.amazon.com/sagemaker/latest/dg/nbi-git-resource.html