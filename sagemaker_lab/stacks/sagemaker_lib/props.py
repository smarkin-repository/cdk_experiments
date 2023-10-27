"""
    Props class for sharing base infra.
"""

from dataclasses import dataclass

@dataclass
class NotebookLabProps:
    """
    Properties for SageMaker Lab

    Args:
        vpc_id (str): The ID of the VPC
        subnet_ids (str): The ID of the subnet for a Notebook instance of SM_LAB
        sg_id (str): The ID of the Security Group
        log (str): The name of the log group
        prefix_name (str): The prefix name of the stack
    """
    vpc_id: str
    subnet_ids: str
    sg_id: str
    log : str
    prefix_name: str


        