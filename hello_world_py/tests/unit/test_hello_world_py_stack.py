import aws_cdk as core
import aws_cdk.assertions as assertions

from hello_world_py.hello_world_py_stack import HelloWorldPyStack

# example tests. To run these tests, uncomment this file along with the example
# resource in hello_world_py/hello_world_py_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = HelloWorldPyStack(app, "hello-world-py")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
