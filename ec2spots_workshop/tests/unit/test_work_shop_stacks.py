import os
import pytest
import sys
import aws_cdk as core
import aws_cdk.assertions as assertions
import requests

sys.path.append(os.path.join(os.path.dirname(__file__), "../../ec2spots_workshop"))


from lib.work_shop_ec2_spot_stack import WorkshopWebAsgStack, WorkshopECSStack
from lib.props import WebAsgProps, ECSProps
from lib.utils import get_latest_linux_ami_from_aws, get_current_env

# This is a sample test case. You can modify it to test the behavior of your
# pytestmark = [pytest.mark.unit, pytest.mark.integration]

# example tests. To run these tests, uncomment this file along with the example
# resource in work_shop_ec2_spot/work_shop_ec2_spot_stack.py
# The snapshot parameter is injected by Pytest -- it's a fixture provided by
# syrupy, the snapshot testing library we're using:
# https://docs.pytest.org/en/stable/explanation/fixtures.html
@pytest.mark.unit
def test_webasg_created(snapshot, env, web_props):
    app = core.App()
    stack = WorkshopWebAsgStack(
        app
        , "work-shop-ec2-spot"
        , props = web_props
        , env = env
    )
    template = assertions.Template.from_stack(stack)
    assert template.to_json() == snapshot


@pytest.mark.unit
def test_ecs_created(ecs_props, env):
    app = core.App()

    stack = WorkshopECSStack(
        app
        , "workshop-ecs-spot"
        , props = ecs_props
        , env = env
    )
    template = assertions.Template.from_stack(stack)
    # https://github.com/cdklabs/aws-cdk-testing-examples/blob/main/python/test/test_processor_stack.py
    template.resource_count_is("AWS::EC2::VPC", 1)
    template.resource_count_is("AWS::AutoScaling::AutoScalingGroup", 1)
    template.resource_count_is("AWS::ElasticLoadBalancingV2::Listener", 1)
    template.resource_count_is("AWS::ElasticLoadBalancingV2::TargetGroup", 1)
    template.resource_count_is("AWS::ECR::Repository", 1)

    # template.has_resource_properties("AWS::VPC::Queue", {
    #     "VisibilityTimeout": 300
    # })

@pytest.mark.integration
def test_web_page(snapshot):
    """
        Make a request to the web page and check the response code.
    """
    code_result = requests.get("https://test.taloni.link").status_code

    assert code_result == 200
