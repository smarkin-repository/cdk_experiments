#!/bin/bash

echo "Hello" > /var/log/hello
echo "Hello" > /home/ec2-user/hello

# sudo stop ecs && sudo start ecs


# sudo yum install ecs-init
# sudo touch /etc/ecs/ecs.config
# sudo cat << 'EOF' > /etc/ecs/ecs.config
# ECS_CLUSTER=Workshop-App-Cluster
# ECS_ENABLE_SPOT_INSTANCE_DRAINING=true
# ECS_CONTAINER_STOP_TIMEOUT=90s
# ECS_ENABLE_CONTAINER_METADATA=true
# EOF
# sudo start ecs.

# sudo chmod 666 /etc/ecs/ecs.config