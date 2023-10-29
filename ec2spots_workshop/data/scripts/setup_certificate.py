import boto3
import os
# Define the ACM certificate ARN
certificate_arn = os.environ("CERTIFICATE_ARN") #'arn:aws:acm:us-east-1:123456789012:certificate/your-certificate-arn'

# Define the path where you want to save the certificate file
local_certificate_path =  os.environ("LOCAL_CERTIFICATE_PATH") # '/path/to/save/certificate.crt'

# Initialize the ACM client
acm_client = boto3.client('acm')

try:
    # Describe the certificate to get its details
    certificate_description = acm_client.describe_certificate(CertificateArn=certificate_arn)

    # Get the certificate body (the actual certificate)
    certificate_body = certificate_description['Certificate']['CertificateBody']

    # Save the certificate to a local file
    with open(local_certificate_path, 'w') as certificate_file:
        certificate_file.write(certificate_body)

    print(f"Certificate downloaded and saved to {local_certificate_path}")
except Exception as e:
    print(f"Error: {e}")