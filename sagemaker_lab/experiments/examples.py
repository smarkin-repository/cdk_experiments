        # vpc = ec2.Vpc.from_lookup(
        #     self, "vpc-workshop",
        #     is_default=False,
        #     owner_account_id="500480925365",
        #     region="us-east-1",
        #     tags={
        #         "Name": "vpc-workshop-lab",
        #         "aws:cloudformation:stack-name": "BaseVPCStack"
        #     }
        # )

        # print(f"VPC: notebook {vpc.vpc_id} ")
        
        # subnet_selection = vpc.select_subnets(
        #     subnet_type=ec2.SubnetType.PUBLIC
        # )

        # role.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))
        # ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),



        # Securety Group
        # sg_sm_name_id = "SageMakerLab-SG-SM"
        # self._sg_sm = ec2.SecurityGroup(
        #     self, sg_sm_name_id,
        #     vpc = props.vpc_id,
        #     allow_all_outbound=True,
        #     security_group_name=sg_sm_name_id,
        #     description=sg_sm_name_id     
        # )

import subprocess
import pprint
import yaml

def sops_decode(file: str, data_type: str, kms_key_arn: str) -> dict:
    sops_args=[
        "sops" , "-d", 
        "--input-type", data_type ,"--output-type", data_type,
        "--verbose",  file
    ]
    result = subprocess.run(sops_args, stdout=subprocess.PIPE)
    secrets = yaml.safe_load(result.stdout)
    return secrets

    # Psevdo code
    # https://stackoverflow.com/questions/4760215/running-shell-command-and-capturing-the-output


import os
print(sops_decode( 
    "".join([os.path.dirname(__file__),"./../configs/dev/","secrets.yaml.enc"])
    , "yaml" 
    , "arn:aws:kms:us-east-1:500480925365:alias/base_kms_key" 
))




# cloudformation = boto3.client('cloudformation')
# stack_name = 'BaseVPCStack'
# res = cloudformation.describe_stacks(StackName=stack_name)
# outputs = res['Stacks'][0]['Outputs']
# print(f"outputs: {outputs}")

# vpc_id = "none"
# for output in outputs:
#     if output.get("OutputKey") == 'VPCID':
#         vpc_id = output.get("OutputValue")

# sg_id = "none"
# for output in outputs:
#     if output.get("OutputKey") == 'ASGSGID':
#         sg_id = output.get("OutputValue")

# Error: All arguments to Vpc.fromLookup() must be concrete (no Tokens)
        _vpc = ec2.Vpc.from_lookup(
            self, "VPCBase",
            vpc_id=props.vpc_id
        )