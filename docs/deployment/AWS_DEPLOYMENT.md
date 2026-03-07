# AWS EC2 Deployment Guide

Deploy the enrollment-assistant stack on AWS: ECR for images, one EC2 instance, and either local Postgres or RDS.

## Prerequisites

- AWS CLI configured (`aws configure`)
- Docker (for building images)
- EC2 key pair for SSH
- For EC2 + RDS: an RDS PostgreSQL instance (pgvector supported)

## 1. ECR: Create repos and log in

```bash
export AWS_REGION=us-west-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

aws ecr create-repository --repository-name enrollment-assistant/agent-api --region $AWS_REGION --image-scanning-configuration scanOnPush=true
aws ecr create-repository --repository-name enrollment-assistant/rag-api --region $AWS_REGION --image-scanning-configuration scanOnPush=true

aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
```

## 2. Build and push images

From repo root:

```bash
./scripts/deploy/aws-push-images.sh
```

## 3. Launch EC2 instance

**Security group**

- **Inbound:** SSH (22) from your IP; Custom TCP 8000 and 8010 from your IP or 0.0.0.0/0.
- **Outbound:** HTTPS (443); if using RDS, allow TCP 5432 to the RDS security group (or use default “all outbound”).
- **RDS (if used):** RDS security group must allow **inbound** TCP 5432 from the **EC2** security group.

**Launch**

```bash
export AWS_REGION=us-west-2
export KEY_NAME=your-key-pair
export SECURITY_GROUP_ID=sg-xxxxxxxx

AMI_ID=$(aws ec2 describe-images --owners amazon --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" "Name=state,Values=available" --query "sort_by(Images, &CreationDate) | [-1].ImageId" --output text --region $AWS_REGION)

aws ec2 run-instances --image-id $AMI_ID --instance-type t3.medium --key-name $KEY_NAME --security-group-ids $SECURITY_GROUP_ID --user-data file://infrastructure/aws/ec2-user-data.sh --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=enrollment-assistant}]' --region $AWS_REGION
```

Get the instance ID from the output, then get the public IP:

```bash
export INSTANCE_ID=i-xxxxxxxx
aws ec2 describe-instances --instance-ids $INSTANCE_ID --query 'Reservations[0].Instances[0].PublicIpAddress' --output text --region $AWS_REGION
```

User-data installs Docker and Docker Compose and creates `/opt/enrollment-assistant`.

## 4. Deploy on EC2

### Option A: EC2 + RDS (recommended)

EC2 runs Agent API (8000) and RAG API (8010); database is on RDS. EC2 and RDS must be in the same VPC; RDS security group must allow inbound 5432 from the EC2 security group.

**Step 1 – Create database on RDS (one-time)**  
From the EC2 instance (RDS is not public), using Docker:

```bash
export RDS_HOST=your-db.xxxx.us-west-2.rds.amazonaws.com
export RDS_PASSWORD='your-rds-password'

docker run --rm --network host postgres:16 psql "host=$RDS_HOST port=5432 dbname=postgres user=postgres sslmode=require password=$RDS_PASSWORD" -c "CREATE DATABASE ragdb;"
docker run --rm --network host postgres:16 psql "host=$RDS_HOST port=5432 dbname=ragdb user=postgres sslmode=require password=$RDS_PASSWORD" -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Step 2 – Copy compose and create `.env`**

From your machine:

```bash
export EC2_IP=1.2.3.4
scp infrastructure/aws/docker-compose.ec2-rds.yml ec2-user@$EC2_IP:/opt/enrollment-assistant/
```

On the instance, create `.env` (replace placeholders):

```bash
cd /opt/enrollment-assistant
cat << 'EOF' > .env
ECR_REGISTRY=123456789012.dkr.ecr.us-west-2.amazonaws.com
IMAGE_TAG=latest
POSTGRES_HOST=your-db.xxxx.us-west-2.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_DB=ragdb
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your-rds-password
POSTGRES_SSLMODE=require
OPENAI_API_KEY=sk-your-openai-key
JWT_SECRET_KEY=your-long-random-secret
EOF
```

Set `ECR_REGISTRY` to `$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com` and the rest to your RDS and keys.

**Step 3 – Start stack**

On the instance:

```bash
cd /opt/enrollment-assistant
aws ecr get-login-password --region us-west-2 | sudo docker login --username AWS --password-stdin $ECR_REGISTRY
docker compose -f docker-compose.ec2-rds.yml up -d
docker compose -f docker-compose.ec2-rds.yml ps
```

If a container is not up, check logs: `docker compose -f docker-compose.ec2-rds.yml logs agent_api` (or `rag_api`).

### Option B: All on EC2 (Postgres on same instance)

```bash
scp infrastructure/aws/docker-compose.ec2.yml ec2-user@$EC2_IP:/opt/enrollment-assistant/
```

On the instance, create `.env` with `ECR_REGISTRY`, `IMAGE_TAG`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `OPENAI_API_KEY`, then:

```bash
aws ecr get-login-password --region us-west-2 | sudo docker login --username AWS --password-stdin $ECR_REGISTRY
docker compose -f docker-compose.ec2.yml up -d
```

Ports: Agent API **8000**, RAG API **8010**, Postgres **5432**.

## 5. Test the API

Replace `EC2_IP` with your instance public IP.

```bash
# Health
curl -s http://EC2_IP:8000/health | jq

# Register (password: 8+ chars, upper, lower, number, special)
curl -s -X POST http://EC2_IP:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"TestPass1!"}' | jq

# OR: login with existing user (form-encoded)
curl -s -X POST http://EC2_IP:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=TestPass1!&grant_type=password" | jq

# Create session (use token from register or login)
export USER_TOKEN="<token from register or login>"
curl -s -X POST http://EC2_IP:8000/api/v1/auth/session \
  -H "Authorization: Bearer $USER_TOKEN" | jq

# Chat (full flow: health -> register/login -> session -> chat)
export SESSION_TOKEN="<session token>"
curl -s -X POST http://EC2_IP:8000/api/v1/chatbot/chat \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"What enrollment options do I have?"}]}' | jq
```

Interactive docs: `http://EC2_IP:8000/docs`.

## 6. Updates and security

- **New image:** Set `IMAGE_TAG` in `.env`, then `docker compose -f docker-compose.ec2-rds.yml pull && docker compose -f docker-compose.ec2-rds.yml up -d`.
- **Secrets:** Keep `.env` out of git; use strong passwords. Prefer Secrets Manager or SSM in production.
- **IAM:** Attach instance profile `AmazonEC2ContainerRegistryReadOnly` so the instance can pull from ECR without stored keys.

## CI/CD (GitHub Actions)

To build images, push to ECR, and optionally deploy to EC2 on push to `main`, see **[CI/CD setup](CI_CD_SETUP.md)**. You’ll configure GitHub secrets (and optionally OIDC with AWS), then the `Deploy to AWS` workflow will run on every push to `main`.

## Troubleshooting

| Issue | What to do |
|------|------------|
| **SSH permission denied** | Use the `.pem` for the key pair set at launch; `chmod 600 ~/.ssh/your-key.pem`. User: `ec2-user` (Amazon Linux) or `ubuntu` (Ubuntu). |
| **InvalidInstanceID.NotFound** | Wrong region or instance terminated. List instances: `aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,State.Name,PublicIpAddress]' --output table --region us-west-2`. |
| **Connection refused to instance** | Security group must allow SSH (22) and ports 8000/8010 from your IP. |
| **agent_api Restarting (1)** | Missing `JWT_SECRET_KEY` or `OPENAI_API_KEY` in `.env`. Add them and use `env_file: .env` in compose; `docker compose up -d --force-recreate`. |
| **database unhealthy / 500 on register** | Set `POSTGRES_SSLMODE=require` in `.env`. Ensure RDS has database `ragdb` and pgvector (Step 1). RDS security group must allow inbound 5432 from EC2 security group. Restart: `docker compose -f docker-compose.ec2-rds.yml restart agent_api`. |
| **RAG API connection refused on 8010** | Security group must allow inbound 8010; check `docker compose ps` and logs for `rag_api`. |
| **Image pull failed** | Run `aws ecr get-login-password --region us-west-2 | sudo docker login ...` again; or attach instance profile with ECR read access. |
