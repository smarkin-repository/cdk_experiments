import aws_cdk as core
from aws_cdk import (
    Stack,
    Duration,
    aws_route53 as route53,
    aws_s3 as s3, 
    aws_ec2 as ec2, 
    aws_kms as kms, 
    aws_iam as iam,
    aws_certificatemanager as acm,
    aws_autoscaling as asg,
    custom_resources as cr, 
    aws_s3_assets as Asset,
    aws_elasticloadbalancingv2 as elbv2
)
from constructs import Construct
from dataclasses import dataclass

import os
import time
import logging
import boto3

from operator import itemgetter
from typing import List, Dict
from .utils import get_my_external_ip



logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

# upper string 
def upper_string(string: str) -> str:
    return string.upper()

class BaseNetworkEnv(Construct):
    
    @property
    def vpc(self):
        return self._vpc
    
    @property 
    def alb(self):
        return self._alb

    @property
    def sg_alb(self):
        return self._sg_alb

    
    def _create_vpc(
            self, id: str, 
            prefix: str, 
            cidr_block: str,
            properties: dict ) -> ec2.Vpc:
        return ec2.Vpc(
            self, id,
            vpc_name=f"{prefix}-workshop-vpc",
            ip_addresses=ec2.IpAddresses.cidr(cidr_block),
            max_azs=3,
            create_internet_gateway=properties.get("create_internet_gateway", False),
            enable_dns_hostnames=properties.get("enable_dns_hostnames", False),
            enable_dns_support=properties.get("enable_dns_support", False),
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name=f"{prefix}-public-subnet",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
                ec2.SubnetConfiguration(
                    name=f"{prefix}-private-subnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
                )
            ]
        )
    def _create_acm_certificate(self, zone_name, domain_name, subjects) -> acm.Certificate:
        # it creats new zone, but I want to reused existing one
        
        # hosted_zone = route53.HostedZone(self, "HostedZone",
        #     zone_name=zone_name
        # )
        hosted_zone = route53.HostedZone.from_hosted_zone_id(self, f"{id}-HostedZone", zone_name)
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
    
    def _create_listener_https(self, alb, port, certifates=None):
        return elbv2.ApplicationListener(
            self, f"{self._prefix.upper()}-ALB-Listener",
            load_balancer=alb,
            port=port,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            certificates=certifates,
        )

    def _create_target_group_https_for_asg(
            self, vpc, targets: list, port: int, health_check: elbv2.HealthCheck):
        return elbv2.ApplicationTargetGroup(
            self, f"{self._prefix.upper()}-ALB-TargetGroup",
            port=port,
            vpc=vpc,  
            target_group_name=f"{self._prefix.upper()}-workshop-tg",
            targets=targets,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            health_check = health_check
        )
    
    def _create_target_group_http_for_asg(
            self, vpc, targets: list, port: int, path_hc: str):
        return elbv2.ApplicationTargetGroup(
            self, f"{self._prefix.upper()}-ALB-TargetGroup",
            port=port, # 
            vpc=vpc,  
            target_group_name=f"{self._prefix.upper()}-workshop-tg",
            targets=targets,
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTP,
            health_check = self._create_health_check_target(port=str(port), path="/")
        )
    


    def _create_securety_group_ingress(self, vpc, ports: list, allow_cidrs: list):
        sg_alb = ec2.SecurityGroup(
            self, f"{self._prefix.upper()}-SecurityGroup",
            vpc=vpc,
            allow_all_outbound=True,
            security_group_name=f"{self._prefix}-alb-sg"
        )
        for port in ports:
            for ip_address in allow_cidrs:
                sg_alb.add_ingress_rule(
                    peer=ec2.Peer.ipv4(ip_address),
                    connection=ec2.Port.tcp(port)
                )
        return sg_alb
    
    def _create_health_check_target(self, port:str, path:str):
        return elbv2.HealthCheck(
                interval=Duration.seconds(60),
                port=port,
                path=path,
                timeout=Duration.seconds(5)
            )

    def _create_alb(self, id:str, prefix:str, internet_facing: bool=False) -> elbv2.ApplicationLoadBalancer:
        """
            Create simple application load balancer with AWS SSL certificats
        """
        return elbv2.ApplicationLoadBalancer(
            self, id,
            vpc=self._vpc,
            internet_facing=internet_facing,
            load_balancer_name=f"{prefix}-workshop-alb",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )

    def get_SG_default(self, id):
        return ec2.SecurityGroup.from_security_group_id(
            self, id, 
            self._vpc.vpc_default_security_group,
            mutable=False
        )

    def create_ssm_endpoint(self):
        ec2.InterfaceVpcEndpoint(
            self, f"{self._prefix.upper()}-VPC-SSM-Endpoint",
            vpc=self._vpc,
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self._props.region}.ssm", 443),
            # Choose which availability zones to place the VPC endpoint in, based on
            # available AZs
            subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_groups=[self.sg_default]
        )

    def create_vpc(self):
        """
        Create VPC with 2 subnets: 2 public and 1 private.
        """

        self._vpc = self._create_vpc(
            id=f"{self._prefix.upper()}-VPC",
            prefix=self._prefix,
            cidr_block=self._props.cidr_block,
            properties=self._props.propertis
        )

    # TODO replace hardcoded values with props
    def create_alb_with_connect_https_to(self, asg, port, port_target, internet_facing=True):
        self._acm_cert = self._create_acm_certificate(
            zone_name="Z0764436UNSJQPH92RK7", #"taloni.link",
            domain_name="test.taloni.link",
            subjects=["*.taloni.link"]
        )
        self._alb = self._create_alb(
            id=f"{self._prefix.upper()}-ALB",
            prefix=self._prefix,
            internet_facing=internet_facing,
        )
        self._sg_alb = self._create_securety_group_ingress(
            vpc=self._vpc,
            ports=[port],
            allow_cidrs=[self._vpc.vpc_cidr_block, get_my_external_ip()]
        )

        self._target_group = self._create_target_group_http_for_asg(
            vpc=self._vpc,
            targets=[asg],
            port=port_target,
            path_hc='/'
        )

        self._alb.add_redirect(
            source_port=80,
            target_port=port,
            source_protocol=elbv2.ApplicationProtocol.HTTP,
            target_protocol=elbv2.ApplicationProtocol.HTTPS,
            open=True
        )

        self._listener = self._create_listener_https(self._alb, port, [self._acm_cert])
        

        self._listener.add_target_groups(
            id=f"{self._prefix.upper()}-ALB-Listener",
            target_groups=[self._target_group]
        )

        self._alb.add_security_group(self._sg_alb)


    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props ,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = props.prefix
        self._props = props
        self.create_vpc()
        self.sg_default = self.get_SG_default(id=f"{self._prefix.upper()}-SG-Default")
