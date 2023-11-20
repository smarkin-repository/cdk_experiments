#!/bin/bash

sudo yum update -y
sudo yum install -y httpd python3 stress-ng docker

sudo sed -i 's/^Listen [0-9]\+/Listen 8080/' /etc/httpd/conf/httpd.conf
sudo systemctl start httpd
sudo systemctl enable httpd
echo '<html><body><h1>Hello {full_name}!</h1></body></html>' > /var/www/html/index.html

# Make sure the 'python3' command is available as 'python'
sudo alternatives --set python /usr/bin/python3

# Install pip for Python 3
sudo curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
sudo python3 /tmp/get-pip.py

pip3 install boto3

# Install Docker
sudo usermod -a -G docker ec2-user
id ec2-user
newgrp docker

sudo systemctl enable docker.service
sudo systemctl start docker.service

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 500480925365.dkr.ecr.us-east-1.amazonaws.com
sudo docker pull 500480925365.dkr.ecr.us-east-1.amazonaws.com/base-repo:latest

