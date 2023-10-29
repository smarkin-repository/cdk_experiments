import aws_cdk as core
from aws_cdk import (
    aws_route53 as route53,
    aws_route53_targets as targets
)


from constructs import Construct
from dataclasses import dataclass

import os
import logging


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

class R53(Construct):
    
    def create_arecord(self, domain_name:str, record_name:str, target):
        zone = route53.HostedZone.from_lookup(
            self, f"{self._prefix}-hosted-zone", 
            domain_name=domain_name
        )
        route53.ARecord(
            self, f"{self._prefix}-arecord",
            zone=zone,
            record_name=record_name,
            delete_existing=True,
            target=route53.RecordTarget(
                alias_target=targets.LoadBalancerTarget(
                    load_balancer=target
                )
            )
        )
    
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            prefix: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = prefix

        
