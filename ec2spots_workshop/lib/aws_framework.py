"""
    Framework for basic elementary of AWS Resources.
"""

import aws_cdk as core
from aws_cdk import (
    aws_iam as iam
    , aws_ec2 as ec2
    , aws_route53 as route53
    , aws_route53_targets as targets
    , aws_certificatemanager as acm,
)


from constructs import Construct
from dataclasses import dataclass

import os
import logging


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

class AWSFramework(Construct):
    def create_arecord(self, id, domain_name:str, record_name:str, target) -> route53.ARecord:
        zone = route53.HostedZone.from_lookup(
            self, f"{id}-{domain_name}", 
            domain_name=domain_name
        )
        return route53.ARecord(
            self, id,
            zone=zone,
            record_name=record_name,
            delete_existing=True,
            target=route53.RecordTarget(
                alias_target=targets.LoadBalancerTarget(
                    load_balancer=target
                )
            )
        )

    def create_securety_group(self, id, name, vpc, ports, allow_ip_addresses=[], description=None) -> ec2.SecurityGroup:        
        sg = ec2.SecurityGroup(
            self, id,
            description=description,
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name=name
        )
        for ip_address in allow_ip_addresses:
            for port in ports:
                sg.add_ingress_rule(
                    peer=ec2.Peer.ipv4(ip_address),
                    connection=ec2.Port.tcp(port)
                )
        return sg

    def create_instance_role(self, id, role_name, description, name_services: list, manage_policies: list=[]) -> iam.Role:
        service_principal = []
        for name_service in name_services:
            service_principal.append(iam.ServicePrincipal(name_service))

        instance_role = iam.Role(
            self, id,
            description=description,
            role_name=role_name,
            assumed_by=iam.CompositePrincipal(
                *service_principal
            )
        )
        self.add_manage_policies(instance_role, manage_policies)
        return instance_role

    def _add_manage_policy(self, instance_role, policy_name):
        instance_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name(policy_name)
        )
    
    def add_manage_policies(self, instance_role: iam.Role, policy_names: list):
        for policy_name in policy_names:
            self._add_manage_policy(instance_role, policy_name)

    def create_acm_certificate(self, hosted_zone_id, domain_name, subjects) -> acm.Certificate:
        # it creats new zone, but I want to reused existing one
        
        # hosted_zone = route53.HostedZone(self, "HostedZone",
        #     zone_name=zone_name
        # )
        hosted_zone = route53.HostedZone.from_hosted_zone_id(self, f"{id}-HostedZone", hosted_zone_id)
        # route53.HostedZone.from_lookup(
        #     self, "MyZone", 
        # )
        # Create ACM certificate
        return acm.Certificate(self, "Certificate",
            domain_name=domain_name,
            subject_alternative_names=subjects,
            certificate_name="Taloni link certificate",
            validation=acm.CertificateValidation.from_dns(hosted_zone)
        )

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        
