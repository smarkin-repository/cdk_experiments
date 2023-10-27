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

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

dirname = os.path.dirname(__file__)

# upper string 
def upper_string(string: str) -> str:
    return string.upper()

@dataclass
class EnvProps:
    cidr_block: str
    prefix: str
    env: core.Environment
    propertis: Dict

class BaseNetworkEnv(Construct):
    
    @property
    def vpc(self):
        return self._vpc
    
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
    
    # create listner for alb 
    def _create_listener(
            self, id: str, alb: elbv2.ApplicationLoadBalancer, 
            certificate: acm.Certificate, 
            port: int, 
            protocol: elbv2.ApplicationProtocol, 
            target_group: elbv2.ApplicationTargetGroup,
            **kwargs
        ) -> elbv2.ApplicationListener:
        return alb.add_listener(
            id=id,
            port=port,
            open=True,
            certificates=[elbv2.ListenerCertificate.from_certificate_manager(certificate)],
            default_action=elbv2.ListenerAction.forward(target_groups=[target_group])
        )
        

    def _create_alb(self, id:str, prefix:str, certificate: acm.Certificate, internet_facing: bool=False) -> elbv2.ApplicationLoadBalancer:
        """
            Create simple application load balancer with AWS SSL certificats
        """
        alb = elbv2.ApplicationLoadBalancer(
            self, id,
            vpc=self._vpc,
            internet_facing=internet_facing,
            load_balancer_name=f"{prefix}-workshop-alb",
            security_group=self.sg_default,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC)
        )        
        # let's check may be neccesary replace this method
        listerner_redirect = alb.add_redirect(
            source_port=80,
            target_port=443,
            source_protocol=elbv2.ApplicationProtocol.HTTP,
            target_protocol=elbv2.ApplicationProtocol.HTTPS,
            open=True
        )
        return alb



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
            service=ec2.InterfaceVpcEndpointService(f"com.amazonaws.{self._props.env.region}.ssm", 443),
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
    def create_alb(self):
        self._acm_cert = self._create_acm_certificate(
            zone_name="Z0764436UNSJQPH92RK7", #"taloni.link",
            domain_name="test.taloni.link",
            subjects=["test.taloni.link"]
        )
        self._alb = self._create_alb(
            id=f"{self._prefix.upper()}-ALB",
            prefix=self._prefix,
            internet_facing=False,
            certificate=self._acm_cert
        )
        self._listener = self._alb.add_listener(
            id=f"{self._prefix.upper()}-ALB-Listener",
            port=443,
            certificates=[self._acm_cert]
        )
        
    def add_target_group_for_alb(self, target: list, port: int):
        self._target_group = elbv2.ApplicationTargetGroup(
            self, f"{self._prefix.upper()}-ALB-TargetGroup",
            port=port, # 
            # open=True,
            # certificates=[self._acm_cert],
            vpc=self._vpc,  
            target_group_name=f"{self._prefix.upper()}-workshop-tg",
            targets=[target],
            target_type=elbv2.TargetType.INSTANCE,
            protocol=elbv2.ApplicationProtocol.HTTPS,
            health_check = elbv2.HealthCheck(
                interval=Duration.seconds(60),
                path="/",
                timeout=Duration.seconds(5)
            )
        )
        self._listener.add_target_groups(
            id=f"{self._prefix.upper()}-ALB-Listener",
            target_groups=[self._target_group]
        )
        
    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props: EnvProps,
            **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._prefix = props.prefix
        self._props = props
        self.create_vpc()
        self.sg_default = self.get_SG_default(id=f"{self._prefix.upper()}-SG-Default")
