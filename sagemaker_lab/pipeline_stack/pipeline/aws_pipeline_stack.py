from aws_cdk import (
    # Duration,
    Stack,
    aws_codecommit as codecommit,
    pipelines as pipelines,
    aws_codebuild as codebuild,
    pipelines as pipelines
    # aws_sqs as sqs,
)
from constructs import Construct
from dataclasses import dataclass


@dataclass
class PipelineProps:
    """
        Props class for sharing base infra.
    """
    prefix_name: str
    
class AwsPipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, 
        props: PipelineProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        pipeline =  pipelines.CodePipeline(self, "Pipeline",
                        pipeline_name=f"{props.prefix_name}-pipeline",
                        synth=pipelines.ShellStep(
                            "Synth",
                            input=pipelines.CodePipelineSource.git_hub(
                                repo_string="smarkin-repository/cdk_experiments", 
                                branch="main"
                            ),
                            commands=[
                                "npm install -g aws-cdk",
                                "python -m pip install -r requirements.txt",
                                "cdk synth",
                                "pytest -v"
                            ]
                        )
                    )
        pipeline.add_stage(
            
        )
        # The code that defines your stack goes here