import boto3
import os
import json

import logging
LOG = logging.getLogger()
LOG.setLevel(logging.INFO)


def delete_stack(stack_name: str) -> dict:
    try:
        cfn = boto3.client("cloudformation")
        cfn.delete_stack(
            StackName=stack_name,
            # OnFailure='ROLLBACK',
            # RetainResources=False
        )
        status_code = 200
        body = f'stack \'{stack_name}\' was deleted successfully'
    except Exception as ex:
        status_code = 500
        body = f'a try to delete stack \'{stack_name}\' was faield'
        LOG.error(ex)
    finally:
        LOG.debug(f"returning response status_code {status_code}")
        return {
            'statusCode' : status_code,
            'body': body
        }
    
def say_hello(stack_name: str) -> str:
    body = f'Hello {stack_name}'
    return {
        'statusCode' : 200,
        'headers': {
            'Content-Type': 'text/path'
        },
        'body': body
    }


def handler(event, context):
    LOG.info(f"Received event: {event}")
    LOG.debug('## ENVIRONMENT VARIABLES')
    LOG.debug(os.environ)
    
    try:
        stack_names = os.environ["STACK_NAMES"]
        status_code = 200
        body = []
        for stack_name in stack_names.split(","):
            LOG.info(f"delete stack {stack_name}...\n")
            result = delete_stack(stack_name=stack_name)
            if result.get("statusCode") == 500:
                status_code = 500
            body.append(result.get("body"))
    except KeyError as ex:
        LOG.error(f"Error: there is not STACK_NAME variable {ex}")
    except Exception as ex:
        LOG.error(f"Error: {ex}")
    return {
            'statusCode' : status_code,
            'headers': {
                'Content-Type': 'text/path'
            },
            'body': body
        }