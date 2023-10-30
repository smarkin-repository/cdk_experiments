"""
Scheduling automated deletion of AWS Cloudformation stacks
https://medium.com/capmo-stories/scheduling-automated-deletion-of-aws-cloudformation-stacks-bffd58ec4cd7
"""

import os
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

import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

@dataclass
class TTLProps:
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
    account: str=None
    region: str=None

class TTL(Construct):
    def __init__(self, scope: Construct, id: str, props: TTLProps, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        
        _lambda_fn = _lambda.Function(
            self, "TTL Lambda",
            runtime=_lambda.Runtime.PYTHON_3_11,
            function_name="ttl_lambda",
            code = _lambda.Code.from_asset(os.path.join(dirname, "../lambda")),
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
                 props: TTLProps, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # add self name to the list of stacks on termination
        props.stack_names.append(self.stack_name)
        props.region = self.region
        props.account = self.account
        self._ttl = TTL(
            self, f"{construct_id}",
            props=props
        )
        
# return Stack with TTL termination stacks get as argumetns of the functions
def ttl_termination_stack_factory(
        scope: Construct, construct_id: str, 
        ttl_props: TTLProps,
        stacks: list,
        env
    ):
    # add all stacks names to ttl_props if it doesn't have terminition protection

    for stack in stacks:
        if stack.termination_protection is True:
            continue
        ttl_props.stack_names.append(stack.stack_name)
        log.info(f"Added stack {stack.stack_name} to TTL termination stack")
    
    log.info("Create TTL termination stack with follow props:")
    log.info(f"{ttl_props}")
    
    return TTLStack(
        scope=scope,
        construct_id=construct_id,
        props=ttl_props,
        env=env
    )