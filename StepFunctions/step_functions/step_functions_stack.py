from aws_cdk import (
    Duration
    , Stack
    , aws_stepfunctions as sfn
    , aws_stepfunctions_tasks as sfn_tasks
    , aws_sns as sns
    , aws_sqs as sqs
    , aws_sns_subscriptions as subscriptions
    , aws_iam as iam
    , aws_batch as batch
)

from constructs import Construct


class StepFunctionsHelloWorld(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

# StateFunction with two states, firest Wait State with 5 second,
# and second Success State 
# https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-wait-state.html
        
        # States

        succeed_state = sfn.Succeed(self, "Succeeded", comment="I'm a Succeeded state")
        start_state = sfn.Pass(self, "Start", comment="Hello, World! I'm a Pass state")
        wait_state = sfn.Wait(
            self, "Wait State", 
            time=sfn.WaitTime.duration(Duration.seconds(5))
        )

        # Create a chain of states. Start State -> Wait State -> Succeed State    
        chain = start_state.next(wait_state).next(succeed_state)
        # Create a state machine with the chain of states.
        state_machine = sfn.StateMachine(
            self, "StateMachine",
            definition=chain,
            timeout=Duration.seconds(60)
        )

# RR: Request Response https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-default
class StepFunctionsRR(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

# StateFunction with two states, firest Wait State with 5 second,
# and second Success State 
# https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-wait-state.html
        # https://docs.aws.amazon.com/step-functions/latest/dg/concepts-input-output-filtering.html

        # Note: A dead-letter queue is optional but it helps capture any failed messages
        dlq = sqs.Queue(
            self,
            id="dead_letter_queue_id",
            retention_period=Duration.days(7)
        )
        
        dead_letter_queue = sqs.DeadLetterQueue(
            max_receive_count=1,
            queue=dlq
        )

        # create SQS queue
        sqs_queue = sqs.Queue(
            self, "MyQueue"
            , visibility_timeout=Duration.seconds(300)
            , dead_letter_queue=dead_letter_queue
            # , queue_name
        )

        # create SNS topic
        sns_topic = sns.Topic(
            self, "MyTopic",
            display_name="MyTopic"
        )

        sns_topic.add_subscription(subscriptions.SqsSubscription(sqs_queue))
        # sqs_queue.grant_consume_messages()
        # sns_topic.grant_publish(self)
        topic_arn = sns_topic.topic_arn
        # States
        succeed_state = sfn.Succeed(self, "Succeeded", comment="I'm a Succeeded state")
        # State witn Wait time that waitting parameter $.timer_seconds
        wait_state = sfn.Wait(
            self, "Wait State", 
            time=sfn.WaitTime.seconds_path("$.timer_seconds")
        )
        # publish a message to a SNS topic 
        rr_state = sfn_tasks.CallAwsService(
            self, "Publish to SNS",
            service="sns",
            action="publish",
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["sns:Publish"],
                    resources=[topic_arn]
                )
            ],
            parameters={"TopicArn": topic_arn, "Message": "Hello, World!"},
            result_path="$.publish_result"
        )

        # Create a chain of states. Start State -> Wait State -> Succeed State    
        chain = wait_state.next(rr_state).next(succeed_state)
        # Create a state machine with the chain of states.
        state_machine = sfn.StateMachine(
            self, "StateMachine",
            definition=chain,
            timeout=Duration.seconds(60)
        )


from .batch_job import BatchJob
# RR: Request Response https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-default
class StepFunctionsRunJob(Stack):
    # https://docs.aws.amazon.com/step-functions/latest/dg/connect-to-resource.html#connect-sync
    # https://docs.aws.amazon.com/step-functions/latest/dg/batch-job-notification.html
    # https://aws.amazon.com/ru/blogs/compute/orchestrating-high-performance-computing-with-aws-step-functions-and-aws-batch/

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create a compute environment
        batch_job  = BatchJob(
            self
            , "BatchJob"
            # , compute_environment_name="computeEnvironmentName", 
            # , job_queue_name="jobQueueName"
        )

        # create Batch Job Definition with compute environment
        # https://docs.aws.amazon.com/batch/latest/userguide/Batch_GetStarted.html

        # create SQS queue
        sqs_queue = sqs.Queue(
            self, "MyQueue"
            , visibility_timeout=Duration.seconds(300)
        )
        
        # create SNS topic
        sns_topic = sns.Topic(
            self, "MyTopic",
            display_name="MyTopic"
        )
        sns_topic.add_subscription(subscriptions.SqsSubscription(sqs_queue))

        # Succeed State
        succeed_state = sfn.Succeed(self, "Succeeded", comment="I'm a Succeeded state")
        # rr_state = sfn.Succeed(self, "Fake State", comment="I'm a Fake state")
        start_state = sfn.Pass(self, "Start", comment="Hello, World! I'm a Pass state")
        # State Submite batch job
        rr_state = sfn_tasks.CallAwsService(
            self, "Run Job",
            service="batch",
            action="submitJob",
            iam_resources=["*"],
            parameters={
                "jobDefinition": "jobDefinition", 
                "jobName": "jobName", 
                "jobQueue": "jobQueue"
            },
            result_path="$.run_job_result"
        )
        # State SNS Publish Notify Successfully Submitted Batch Job
        sns_success_state = sfn_tasks.CallAwsService(
            self, "Publish Successfully state  to SNS",
            service="sns",
            action="publish",
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["sns:Publish"],
                    resources=[sns_topic.topic_arn]
                )
            ]
            , parameters={"TopicArn": sns_topic.topic_arn, "Message": "Successfully Submitted Batch Job"}
            , result_path="$.publish_result"
            , output_path="$.publish_output"
            , heartbeat=Duration.seconds(60)
        )
        
        # State SNS Publish Notify Failured  Submitted Batch Job
        sns_failured_state = sfn_tasks.CallAwsService(
            self, "Publish Failured state to SNS",
            service="sns",
            action="publish",
            iam_resources=["*"],
            additional_iam_statements=[
                iam.PolicyStatement(
                    actions=["sns:Publish"],
                    resources=[sns_topic.topic_arn]
                    )
            ]
            , parameters={"TopicArn": sns_topic.topic_arn, "Message": "Failured  Submitted Batch Job"}
            , result_path="$.publish_result"
            , output_path="$.publish_output"
            , heartbeat=Duration.seconds(60)
            # , catch=sfn.Catch.all()
        )



        # Create a chain of states. Start State -> RR State -> 
        # Choise sns_success_state If when Succeeded else sns_failured_state
        # https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-choice-state.html
        # https://docs.aws.amazon.com/step-functions/latest/dg/tutorial-choice-state.html
        condition = sfn.Condition.string_equals("$.run_job_result.status", "SUCCEEDED")
        choice = sfn.Choice(self, "Choice State").when(
            condition, sns_success_state).otherwise(sns_failured_state)
        chain = start_state.next(rr_state).next(choice)
        
          
        # Create a state machine with the chain of states.
        state_machine = sfn.StateMachine(
            self, "StateMachine",
            definition=chain,
            timeout=Duration.seconds(60)
        )