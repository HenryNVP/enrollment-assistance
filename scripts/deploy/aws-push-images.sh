#!/bin/bash
# Build and push Docker images to AWS ECR

set -e

# Configuration
AWS_REGION="${AWS_REGION:-us-west-2}"
VERSION="${VERSION:-latest}"
USE_LITE_RAG="${USE_LITE_RAG:-true}"  # Use Dockerfile.lite for RAG API (no sentence_transformers)
SCRIPT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Building and Pushing Images to AWS ECR ===${NC}\n"

# Get AWS account ID
echo "Getting AWS account ID..."
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null)
if [ -z "$AWS_ACCOUNT_ID" ]; then
    echo "Error: AWS CLI not configured. Run 'aws configure' first."
    exit 1
fi

ECR_BASE="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
AGENT_IMAGE="$ECR_BASE/enrollment-assistant/agent-api:$VERSION"
RAG_IMAGE="$ECR_BASE/enrollment-assistant/rag-api:$VERSION"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Region: $AWS_REGION"
echo "  Account: $AWS_ACCOUNT_ID"
echo "  Version: $VERSION"
echo "  Agent API: $AGENT_IMAGE"
echo "  RAG API: $RAG_IMAGE"
echo ""

# Login to ECR
echo -e "${BLUE}Logging in to ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_BASE || {
    echo "Error: Failed to login to ECR. Check your AWS credentials."
    exit 1
  }
echo -e "${GREEN}✓ Logged in to ECR${NC}\n"

# Build and push Agent API
echo -e "${BLUE}Building Agent API...${NC}"
cd "$SCRIPT_DIR/backend/services/agent_ai"
docker build -t $AGENT_IMAGE .
echo -e "${GREEN}✓ Agent API built${NC}"

echo -e "${BLUE}Pushing Agent API...${NC}"
docker push $AGENT_IMAGE
echo -e "${GREEN}✓ Agent API pushed: $AGENT_IMAGE${NC}\n"

# Build and push RAG API
if [ "$USE_LITE_RAG" = "true" ]; then
    echo -e "${BLUE}Building RAG API (lite - using external embedding APIs, no sentence_transformers)...${NC}"
    cd "$SCRIPT_DIR/backend/services/rag_api"
    docker build -f Dockerfile.lite -t $RAG_IMAGE .
    echo -e "${GREEN}✓ RAG API built (lite version - optimized for external embeddings)${NC}"
else
    echo -e "${BLUE}Building RAG API (full - includes sentence_transformers)...${NC}"
    cd "$SCRIPT_DIR/backend/services/rag_api"
    docker build -t $RAG_IMAGE .
    echo -e "${GREEN}✓ RAG API built (full version)${NC}"
fi

echo -e "${BLUE}Pushing RAG API...${NC}"
docker push $RAG_IMAGE
echo -e "${GREEN}✓ RAG API pushed: $RAG_IMAGE${NC}\n"

echo -e "${GREEN}=== All images pushed successfully! ===${NC}"
echo ""
echo "Next steps:"
echo "  1. Create ECS task definition"
echo "  2. Deploy to ECS service"
echo "  3. Or use these images in your deployment"
