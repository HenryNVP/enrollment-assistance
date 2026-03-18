#!/bin/bash
# Deploy services to AWS App Runner

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== AWS App Runner Deployment ===${NC}\n"

# Check prerequisites
if ! command -v aws &> /dev/null; then
    echo -e "${RED}Error: AWS CLI not installed${NC}"
    exit 1
fi

# Get RDS endpoint (user must provide)
read -p "Enter RDS endpoint (e.g., db.xxx.us-west-2.rds.amazonaws.com): " RDS_ENDPOINT
if [ -z "$RDS_ENDPOINT" ]; then
    echo -e "${RED}Error: RDS endpoint is required${NC}"
    exit 1
fi

# Get secrets ARNs
read -p "Enter Secrets Manager ARN for DB password (or press Enter to use default): " DB_PASSWORD_ARN
DB_PASSWORD_ARN="${DB_PASSWORD_ARN:-arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:enrollment-assistant/db-password}"

read -p "Enter Secrets Manager ARN for OpenAI API key (or press Enter to use default): " OPENAI_KEY_ARN
OPENAI_KEY_ARN="${OPENAI_KEY_ARN:-arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:enrollment-assistant/openai-api-key}"

read -p "Enter Secrets Manager ARN for JWT secret (or press Enter to use default): " JWT_SECRET_ARN
JWT_SECRET_ARN="${JWT_SECRET_ARN:-arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:enrollment-assistant/jwt-secret}"

# IAM Role ARN
read -p "Enter App Runner IAM role ARN (or press Enter to create default): " IAM_ROLE_ARN
if [ -z "$IAM_ROLE_ARN" ]; then
    echo -e "${YELLOW}Creating IAM role for App Runner...${NC}"
    # Note: This is a simplified version - you may need to create the role manually
    echo "Please create IAM role manually or provide existing role ARN"
    exit 1
fi

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Region: $AWS_REGION"
echo "  Account: $AWS_ACCOUNT_ID"
echo "  RDS Endpoint: $RDS_ENDPOINT"
echo ""

# Deploy RAG API
echo -e "${BLUE}Deploying RAG API...${NC}"

RAG_SERVICE_ARN=$(aws apprunner create-service \
  --service-name enrollment-assistant-rag-api \
  --source-configuration "{
    \"ImageRepository\": {
      \"ImageIdentifier\": \"${ECR_BASE}/enrollment-assistant/rag-api:latest\",
      \"ImageConfiguration\": {
        \"Port\": \"8000\",
        \"RuntimeEnvironmentVariables\": {
          \"PORT\": \"8000\",
          \"RAG_HOST\": \"0.0.0.0\",
          \"RAG_PORT\": \"8000\",
          \"DB_HOST\": \"${RDS_ENDPOINT}\",
          \"DB_PORT\": \"5432\",
          \"POSTGRES_DB\": \"ragdb\",
          \"POSTGRES_USER\": \"postgres\",
          \"VECTOR_DB_TYPE\": \"pgvector\",
          \"EMBEDDINGS_PROVIDER\": \"openai\",
          \"COLLECTION_NAME\": \"policy_docs\"
        },
        \"RuntimeEnvironmentSecrets\": {
          \"POSTGRES_PASSWORD\": \"${DB_PASSWORD_ARN}\",
          \"OPENAI_API_KEY\": \"${OPENAI_KEY_ARN}\",
          \"JWT_SECRET\": \"${JWT_SECRET_ARN}\"
        }
      },
      \"ImageRepositoryType\": \"ECR\"
    },
    \"AutoDeploymentsEnabled\": false
  }" \
  --instance-configuration "{
    \"Cpu\": \"1 vCPU\",
    \"Memory\": \"2 GB\",
    \"InstanceRoleArn\": \"${IAM_ROLE_ARN}\"
  }" \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' \
  --region $AWS_REGION \
  --query 'Service.ServiceArn' \
  --output text 2>&1) || {
    echo -e "${YELLOW}Service may already exist. Getting existing service ARN...${NC}"
    RAG_SERVICE_ARN=$(aws apprunner list-services \
      --region $AWS_REGION \
      --query "ServiceSummaryList[?ServiceName=='enrollment-assistant-rag-api'].ServiceArn" \
      --output text)
}

if [ -z "$RAG_SERVICE_ARN" ] || [ "$RAG_SERVICE_ARN" = "None" ]; then
    echo -e "${RED}Failed to create or find RAG API service${NC}"
    exit 1
fi

echo -e "${GREEN}✓ RAG API service created/found: ${RAG_SERVICE_ARN}${NC}"

# Wait for service to be ready and get URL
echo -e "${YELLOW}Waiting for RAG API service to be ready...${NC}"
sleep 30

RAG_API_URL=$(aws apprunner describe-service \
  --service-arn "$RAG_SERVICE_ARN" \
  --region $AWS_REGION \
  --query 'Service.ServiceUrl' \
  --output text)

echo -e "${GREEN}✓ RAG API URL: ${RAG_API_URL}${NC}\n"

# Deploy Agent API
echo -e "${BLUE}Deploying Agent API...${NC}"

AGENT_SERVICE_ARN=$(aws apprunner create-service \
  --service-name enrollment-assistant-agent-api \
  --source-configuration "{
    \"ImageRepository\": {
      \"ImageIdentifier\": \"${ECR_BASE}/enrollment-assistant/agent-api:latest\",
      \"ImageConfiguration\": {
        \"Port\": \"8000\",
        \"RuntimeEnvironmentVariables\": {
          \"PORT\": \"8000\",
          \"POSTGRES_HOST\": \"${RDS_ENDPOINT}\",
          \"POSTGRES_PORT\": \"5432\",
          \"POSTGRES_DB\": \"ragdb\",
          \"POSTGRES_USER\": \"postgres\",
          \"DEFAULT_LLM_MODEL\": \"gpt-4o-mini\",
          \"RAG_BASE_URL\": \"https://${RAG_API_URL}\"
        },
        \"RuntimeEnvironmentSecrets\": {
          \"POSTGRES_PASSWORD\": \"${DB_PASSWORD_ARN}\",
          \"OPENAI_API_KEY\": \"${OPENAI_KEY_ARN}\",
          \"JWT_SECRET_KEY\": \"${JWT_SECRET_ARN}\"
        }
      },
      \"ImageRepositoryType\": \"ECR\"
    },
    \"AutoDeploymentsEnabled\": false
  }" \
  --instance-configuration "{
    \"Cpu\": \"1 vCPU\",
    \"Memory\": \"2 GB\",
    \"InstanceRoleArn\": \"${IAM_ROLE_ARN}\"
  }" \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }' \
  --region $AWS_REGION \
  --query 'Service.ServiceArn' \
  --output text 2>&1) || {
    echo -e "${YELLOW}Service may already exist. Getting existing service ARN...${NC}"
    AGENT_SERVICE_ARN=$(aws apprunner list-services \
      --region $AWS_REGION \
      --query "ServiceSummaryList[?ServiceName=='enrollment-assistant-agent-api'].ServiceArn" \
      --output text)
}

if [ -z "$AGENT_SERVICE_ARN" ] || [ "$AGENT_SERVICE_ARN" = "None" ]; then
    echo -e "${RED}Failed to create or find Agent API service${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Agent API service created/found: ${AGENT_SERVICE_ARN}${NC}"

# Wait and get Agent API URL
echo -e "${YELLOW}Waiting for Agent API service to be ready...${NC}"
sleep 30

AGENT_API_URL=$(aws apprunner describe-service \
  --service-arn "$AGENT_SERVICE_ARN" \
  --region $AWS_REGION \
  --query 'Service.ServiceUrl' \
  --output text)

echo -e "${GREEN}✓ Agent API URL: ${AGENT_API_URL}${NC}\n"

echo -e "${GREEN}=== Deployment Complete! ===${NC}\n"
echo "Service URLs:"
echo "  RAG API:   https://${RAG_API_URL}"
echo "  Agent API: https://${AGENT_API_URL}"
echo ""
echo "Next steps:"
echo "  1. Test health endpoints:"
echo "     curl https://${RAG_API_URL}/health"
echo "     curl https://${AGENT_API_URL}/health"
echo "  2. Monitor services in AWS Console"
echo "  3. Check CloudWatch logs for any issues"
