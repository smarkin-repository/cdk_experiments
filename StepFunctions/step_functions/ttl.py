"""
Scheduling automated deletion of AWS Cloudformation stacks
https://medium.com/capmo-stories/scheduling-automated-deletion-of-aws-cloudformation-stacks-bffd58ec4cd7
"""

import aws_cdk as core

from aws_cdk import (
    CfnOutput,
    Stack,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_iam as iam,
    aws_lambda as _lambda,
)

from constructs import Construct
from dataclasses import dataclass

@dataclass
class TTLStackProps:
    """
    Properties for TTL
    
    Args:
        stack_names (str): The name of the stacks
        ttl (int): The number of minutes to retain the stack
        account (str): The account ID
        region (str): The region
        prefix_name (str): The prefix name of the stack
    """
    prefix_name: str
    stack_names: list
    ttl: int
    account: str
    region: str

class TTL(Construct):
    def __init__(self, scope: Construct, id: str, props: TTLStackProps, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        _lambda_fn = _lambda.Function(
            self, "TTL Lambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            function_name="ttl_lambda",
            code = _lambda.Code.from_asset("lambda"),
            handler='ttl.handler',
            environment={
                "STACK_NAMES": ",".join(props.stack_names),
            }
        )

        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_events.Schedule.html
        # https://docs.aws.amazon.com/cdk/api/v2/docs/aws-cdk-lib.aws_events-readme.html
        # https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html
        # https://edwinradtke.com/eventtargets
        # https://crontab.cronhub.io/

        rule = events.Rule(
            self, "Trigger Lambda",
            schedule=events.Schedule.rate(core.Duration.minutes(props.ttl)),
            # schedule=events.Schedule.cron(
            #     minute="*/1",
            #     hour="*",
            #     day="*",
            #     month="*",
            # )
        )
        rule.add_target(events_targets.LambdaFunction(_lambda_fn))

        # Allow CF operations
        # https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_principal.html        
        for stack_name in props.stack_names:
            statement = iam.PolicyStatement(
                resources=[
                    f'arn:aws:cloudformation:{props.region}:{props.account}:stack/{stack_name}', 
                    f'arn:aws:cloudformation:{props.region}:{props.account}:stack/{stack_name}/*', 
                ],
                actions=[
                    'cloudformation:DescribeStacks',
                    'cloudformation:DeleteStack',
                ]
            )

            _lambda_fn.add_to_role_policy(statement)
        
        # CfnOutput(
        #     self, "Stack TTL value", 
        #     export_name=f"${props.prefix_name}-ttl-timer-value", 
        #     value=f"{props.ttl}"
        # )

        # CfnOutput(
        #     self, "Stack names", 
        #     export_name=f"${props.prefix_name}-ttl-stack-names", 
        #     value=",".join(props.stack_names)
        # )

class TTLStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, 
                 props: TTLStackProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # add self name to the list of stacks on termination
        props.stack_names.append(self.stack_name)

        self._ttl = TTL(
            self, f"{construct_id}",
            props=props
        )