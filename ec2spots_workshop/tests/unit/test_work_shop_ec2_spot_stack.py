import os
import sys
import aws_cdk as core
import aws_cdk.assertions as assertions

sys.path.append(os.path.join(os.path.dirname(__file__), "../../ec2spots_workshop"))


from lib.work_shop_ec2_spot_stack import WorkshopWebAsgStack
from lib.props import WebAsgProps
from lib.utils import get_latest_linux_ami_from_aws, get_current_env

# example tests. To run these tests, uncomment this file along with the example
# resource in work_shop_ec2_spot/work_shop_ec2_spot_stack.py
# The snapshot parameter is injected by Pytest -- it's a fixture provided by
# syrupy, the snapshot testing library we're using:
# https://docs.pytest.org/en/stable/explanation/fixtures.html
def test_sqs_queue_created(snapshot):
    app = core.App()
    os.environ["CDK_DEFAULT_ACCOUNT"]="500480925365"
    os.environ["CDK_DEFAULT_REGION"]="us-east-1"
    env = get_current_env()
    ami_image = get_latest_linux_ami_from_aws(
        region=env.region
        , pattern={
                "owner" : "amazon",
                "architecture" : "x86_64",
                "name" : "amzn2-ami-hvm-*"
        }
    )

    prefix = "workshop"
    web_props = WebAsgProps(
        prefix=prefix
        , cidr_block="172.30.0.0/24"
        , propertis={
            "create_internet_gateway":True,
            "enable_dns_hostnames":True,
            "enable_dns_support":True,
        }
        , instance_type="t3.small"
        , spot_types=[
            "t3.small"
            ,"t4g.small"
        ]
        , min_capacity=1
        , max_capacity=2
        , desired_capacity=1
        , ami_image=ami_image
        , domain_name="taloni.link"
        , record_name="test"
        , data_path="../data"
    )


    stack = WorkshopWebAsgStack(
        app
        , "work-shop-ec2-spot"
        , props = web_props
        , env = env
    )
    template = assertions.Template.from_stack(stack)
    assert template.to_json() == snapshot
