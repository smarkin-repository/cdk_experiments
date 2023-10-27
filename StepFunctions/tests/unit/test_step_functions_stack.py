import aws_cdk as core
import aws_cdk.assertions as assertions

from step_functions.step_functions_stack import StepFunctionsStack

# example tests. To run these tests, uncomment this file along with the example
# resource in step_functions/step_functions_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = StepFunctionsStack(app, "step-functions")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
