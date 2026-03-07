# AWS App Runner Deployment Guide

This guide covers deploying the enrollment assistant services to AWS App Runner, a fully managed service for containerized applications.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Setup Secrets in AWS Secrets Manager](#setup-secrets-in-aws-secrets-manager)
3. [Create RDS Database](#create-rds-database)
4. [Deploy RAG API](#deploy-rag-api)
5. [Deploy Agent API](#deploy-agent-api)
6. [Configure Service Communication](#configure-service-communication)
7. [Monitoring and Logging](#monitoring-and-logging)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

- AWS CLI configured with appropriate permissions
- Docker images pushed to ECR (see [AWS_DEPLOYMENT.md](./AWS_DEPLOYMENT.md))
- RDS PostgreSQL database with pgvector extension
- AWS Secrets Manager access

## Setup Secrets in AWS Secrets Manager

### 1. Create Secrets

```bash
# Set your region and account ID
export AWS_REGION=us-west-2
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create database password secret
aws secretsmanager create-secret \
  --name enrollment-assistant/db-password \
  --description "PostgreSQL database password" \
  --secret-string "your-database-password" \
  --region $AWS_REGION

# Create OpenAI API key secret
aws secretsmanager create-secret \
  --name enrollment-assistant/openai-api-key \
  --description "OpenAI API key" \
  --secret-string "sk-your-openai-api-key" \
  --region $AWS_REGION

# Create JWT secret
aws secretsmanager create-secret \
  --name enrollment-assistant/jwt-secret \
  --description "JWT secret key for authentication" \
  --secret-string "your-jwt-secret-key" \
  --region $AWS_REGION
```

### 2. Update Secret Values (if needed)

```bash
aws secretsmanager update-secret \
  --secret-id enrollment-assistant/openai-api-key \
  --secret-string "sk-new-key" \
  --region $AWS_REGION
```

## Create RDS Database

### Option 1: Using AWS CLI

```bash
# Create RDS PostgreSQL instance with pgvector
aws rds create-db-instance \
  --db-instance-identifier enrollment-assistant-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.1 \
  --master-username postgres \
  --master-user-password your-password \
  --allocated-storage 20 \
  --storage-type gp2 \
  --vpc-security-group-ids sg-xxx \
  --db-subnet-group-name your-subnet-group \
  --backup-retention-period 7 \
  --region $AWS_REGION

# Wait for instance to be available
aws rds wait db-instance-available \
  --db-instance-identifier enrollment-assistant-db \
  --region $AWS_REGION

# Get endpoint
aws rds describe-db-instances \
  --db-instance-identifier enrollment-assistant-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text \
  --region $AWS_REGION
```

### Option 2: Using AWS Console

1. Go to RDS Console
2. Create database → PostgreSQL
3. Enable pgvector extension (install after creation)
4. Note the endpoint URL

### 3. Install pgvector Extension

Connect to your RDS instance and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## Deploy RAG API

### Option 1: Using AWS Console

1. **Go to App Runner Console**
   - Navigate to AWS App Runner
   - Click "Create service"

2. **Source Configuration**
   - Source: Container registry
   - Provider: Amazon ECR
   - Container image URI: `000377555391.dkr.ecr.us-west-2.amazonaws.com/enrollment-assistant/rag-api:latest`
   - Deployment trigger: Manual (or Automatic)

3. **Service Settings**
   - Service name: `enrollment-assistant-rag-api`
   - Virtual CPU: 1 vCPU
   - Memory: 2 GB
   - Port: 8000

4. **Environment Variables**
   ```
   PORT=8000
   RAG_HOST=0.0.0.0
   RAG_PORT=8000
   DB_HOST=your-rds-endpoint.region.rds.amazonaws.com
   DB_PORT=5432
   POSTGRES_DB=ragdb
   POSTGRES_USER=postgres
   VECTOR_DB_TYPE=pgvector
   EMBEDDINGS_PROVIDER=openai
   COLLECTION_NAME=policy_docs
   ```

5. **Secrets**
   - Add secrets from Secrets Manager:
     - `POSTGRES_PASSWORD` → `enrollment-assistant/db-password`
     - `OPENAI_API_KEY` → `enrollment-assistant/openai-api-key`
     - `JWT_SECRET` → `enrollment-assistant/jwt-secret`

6. **Health Check**
   - Protocol: HTTP
   - Path: `/health`
   - Interval: 10 seconds
   - Timeout: 5 seconds
   - Healthy threshold: 1
   - Unhealthy threshold: 5

7. **Auto Scaling**
   - Min: 1
   - Max: 10
   - Concurrency: 100

8. **Create Service**

### Option 2: Using AWS CLI

```bash
# Create App Runner service for RAG API
aws apprunner create-service \
  --service-name enrollment-assistant-rag-api \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "000377555391.dkr.ecr.us-west-2.amazonaws.com/enrollment-assistant/rag-api:latest",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "PORT": "8000",
          "RAG_HOST": "0.0.0.0",
          "RAG_PORT": "8000",
          "DB_HOST": "your-rds-endpoint.region.rds.amazonaws.com",
          "DB_PORT": "5432",
          "POSTGRES_DB": "ragdb",
          "POSTGRES_USER": "postgres",
          "VECTOR_DB_TYPE": "pgvector",
          "EMBEDDINGS_PROVIDER": "openai",
          "COLLECTION_NAME": "policy_docs"
        },
        "RuntimeEnvironmentSecrets": {
          "POSTGRES_PASSWORD": "arn:aws:secretsmanager:us-west-2:000377555391:secret:enrollment-assistant/db-password",
          "OPENAI_API_KEY": "arn:aws:secretsmanager:us-west-2:000377555391:secret:enrollment-assistant/openai-api-key",
          "JWT_SECRET": "arn:aws:secretsmanager:us-west-2:000377555391:secret:enrollment-assistant/jwt-secret"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": false
  }' \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB",
    "InstanceRoleArn": "arn:aws:iam::000377555391:role/apprunner-service-role"
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' \
  --auto-scaling-configuration-arn "arn:aws:apprunner:us-west-2:000377555391:autoscalingconfiguration/DefaultConfiguration/1/0000000000000001" \
  --region us-west-2
```

### Option 3: Using Terraform (Recommended for Production)

See `infrastructure/aws/apprunner/terraform/` for Terraform configurations.

## Deploy Agent API

### Steps

1. **Get RAG API Service URL**
   ```bash
   aws apprunner describe-service \
     --service-arn arn:aws:apprunner:us-west-2:000377555391:service/enrollment-assistant-rag-api/xxx \
     --query 'Service.ServiceUrl' \
     --output text
   ```

2. **Create Agent API Service**
   - Similar to RAG API, but use:
     - Image: `enrollment-assistant/agent-api:latest`
     - Service name: `enrollment-assistant-agent-api`
     - Environment variable: `RAG_BASE_URL=https://your-rag-api-service-url`

### Using AWS CLI

```bash
# Get RAG API URL first
RAG_API_URL=$(aws apprunner describe-service \
  --service-arn arn:aws:apprunner:us-west-2:000377555391:service/enrollment-assistant-rag-api/xxx \
  --query 'Service.ServiceUrl' \
  --output text)

# Create Agent API service
aws apprunner create-service \
  --service-name enrollment-assistant-agent-api \
  --source-configuration "{
    \"ImageRepository\": {
      \"ImageIdentifier\": \"000377555391.dkr.ecr.us-west-2.amazonaws.com/enrollment-assistant/agent-api:latest\",
      \"ImageConfiguration\": {
        \"Port\": \"8000\",
        \"RuntimeEnvironmentVariables\": {
          \"PORT\": \"8000\",
          \"POSTGRES_HOST\": \"your-rds-endpoint.region.rds.amazonaws.com\",
          \"POSTGRES_PORT\": \"5432\",
          \"POSTGRES_DB\": \"ragdb\",
          \"POSTGRES_USER\": \"postgres\",
          \"DEFAULT_LLM_MODEL\": \"gpt-4o-mini\",
          \"RAG_BASE_URL\": \"${RAG_API_URL}\"
        },
        \"RuntimeEnvironmentSecrets\": {
          \"POSTGRES_PASSWORD\": \"arn:aws:secretsmanager:us-west-2:000377555391:secret:enrollment-assistant/db-password\",
          \"OPENAI_API_KEY\": \"arn:aws:secretsmanager:us-west-2:000377555391:secret:enrollment-assistant/openai-api-key\",
          \"JWT_SECRET_KEY\": \"arn:aws:secretsmanager:us-west-2:000377555391:secret:enrollment-assistant/jwt-secret\"
        }
      },
      \"ImageRepositoryType\": \"ECR\"
    },
    \"AutoDeploymentsEnabled\": false
  }" \
  --instance-configuration '{
    "Cpu": "1 vCPU",
    "Memory": "2 GB",
    "InstanceRoleArn": "arn:aws:iam::000377555391:role/apprunner-service-role"
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' \
  --region us-west-2
```

## Configure Service Communication

### IAM Role for App Runner

App Runner needs an IAM role to:
- Pull images from ECR
- Access Secrets Manager
- Write CloudWatch logs

```bash
# Create IAM role for App Runner
aws iam create-role \
  --role-name apprunner-service-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name apprunner-service-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess

# Create and attach custom policy for Secrets Manager
aws iam put-role-policy \
  --role-name apprunner-service-role \
  --policy-name SecretsManagerAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:enrollment-assistant/*"
    }]
  }'
```

## Monitoring and Logging

### View Logs

```bash
# View RAG API logs
aws apprunner list-operations \
  --service-arn arn:aws:apprunner:us-west-2:000377555391:service/enrollment-assistant-rag-api/xxx

# View logs in CloudWatch
aws logs tail /aws/apprunner/enrollment-assistant-rag-api/service --follow
```

### Metrics

App Runner automatically sends metrics to CloudWatch:
- `CPUUtilization`
- `MemoryUtilization`
- `RequestCount`
- `RequestLatency`
- `ActiveInstances`

## Troubleshooting

### Common Issues

1. **Service fails to start**
   - Check CloudWatch logs
   - Verify environment variables
   - Check IAM role permissions
   - Verify ECR image exists

2. **Health check failures**
   - Verify `/health` endpoint works
   - Check port configuration
   - Review security group settings

3. **Database connection errors**
   - Verify RDS endpoint is correct
   - Check security group allows App Runner IPs
   - Verify database credentials in Secrets Manager

4. **Service-to-service communication**
   - Use App Runner service URLs (HTTPS)
   - Verify `RAG_BASE_URL` is set correctly
   - Check both services are in same VPC (if using VPC connector)

### Useful Commands

```bash
# Get service status
aws apprunner describe-service \
  --service-arn <service-arn> \
  --region us-west-2

# List all services
aws apprunner list-services --region us-west-2

# Update service (redeploy)
aws apprunner start-deployment \
  --service-arn <service-arn> \
  --region us-west-2

# Delete service
aws apprunner delete-service \
  --service-arn <service-arn> \
  --region us-west-2
```

## Cost Optimization

- **Use appropriate instance sizes**: Start with 1 vCPU, 2 GB memory
- **Configure auto-scaling**: Set min=1, max based on traffic
- **Enable auto-deployments**: Only for non-production
- **Monitor costs**: Use AWS Cost Explorer

## Next Steps

- Set up custom domain with Route 53
- Configure VPC connector for private RDS access
- Set up CloudWatch alarms
- Configure CI/CD for automatic deployments
- Add CloudFront for CDN
