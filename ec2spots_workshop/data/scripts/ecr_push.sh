#!/bin/bash

region="us-east-1"
aws_account_id="500480925365"
image_id="802d72a223f0"
image_tag="latest"

aws ecr get-login-password --region $region | docker login --username AWS --password-stdin "$aws_account_id.dkr.ecr.$region.amazonaws.com"
docker tag $image_id $aws_account_id.dkr.ecr.$region.amazonaws.com/base-repo:$image_tag
docker push $aws_account_id.dkr.ecr.$region.amazonaws.com/base-repo:$image_tag

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 500480925365.dkr.ecr.us-east-1.amazonaws.com
