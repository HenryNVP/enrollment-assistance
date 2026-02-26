#!/bin/bash
# EC2 user data: install Docker and Docker Compose (Amazon Linux 2).
# Use this when launching an instance to run the enrollment-assistant stack.
# After boot, SSH in and deploy with docker compose (see docs/deployment/AWS_DEPLOYMENT.md).

set -e

# Docker (Amazon Linux 2)
yum update -y
yum install -y docker
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# Docker Compose (standalone)
DCOMPOSE_VERSION="v2.24.0"
curl -L "https://github.com/docker/compose/releases/download/${DCOMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose

# Optional: create app directory for deploy
mkdir -p /opt/enrollment-assistant
chown ec2-user:ec2-user /opt/enrollment-assistant
