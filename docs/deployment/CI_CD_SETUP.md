# CI/CD with GitHub and AWS

This guide sets up GitHub Actions to run tests (CI) and to build, push to ECR, and optionally deploy to EC2 (CD) on push to `main`.

## Overview

- **CI** (`.github/workflows/ci.yml`): runs on push/PR to `main` and `develop` — unit tests, integration tests, lint.
- **CD** (`.github/workflows/deploy-aws.yml`): runs on push to `main` — builds Docker images, pushes to ECR, and optionally SSHs to EC2 to run `docker compose pull && up -d`.

## 1. GitHub secrets (required for CD)

In **GitHub repo → Settings → Secrets and variables → Actions**, add:

| Secret | Required | Description |
|--------|----------|-------------|
| `AWS_ACCOUNT_ID` | Yes (for CD) | Your AWS account ID (e.g. `123456789012`). |
| `AWS_ROLE_ARN` | Yes (for CD, if using OIDC) | IAM role ARN for GitHub OIDC (see below). |
| `EC2_HOST` | No | EC2 instance public IP or hostname (e.g. `35.91.178.45`). If set with `EC2_SSH_PRIVATE_KEY`, deploy job will run. |
| `EC2_SSH_PRIVATE_KEY` | No | Full contents of the `.pem` file used to SSH to EC2 (e.g. `ec2-user@$EC2_HOST`). |

**Optional (instead of OIDC):** use long-lived AWS keys for the build job:

| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | IAM user access key with ECR push rights. |
| `AWS_SECRET_ACCESS_KEY` | IAM user secret key. |

If you use these, you must change the workflow to use them instead of `role-to-assume` (see comment in `.github/workflows/deploy-aws.yml`).

## 2. AWS auth: OIDC (recommended) or static keys

### Option A: OIDC (no long-lived AWS keys)

1. **Create an OIDC identity provider in IAM** (once per account or reuse existing):
   - IAM → Identity providers → Add provider.
   - Provider type: **OpenID Connect**.
   - Provider URL: `https://token.actions.githubusercontent.com`.
   - Audience: `sts.amazonaws.com`.

2. **Create an IAM role for GitHub**:
   - IAM → Roles → Create role → Custom trust policy.
   - Trust policy (replace `YOUR_ORG/YOUR_REPO` with your repo, e.g. `myorg/enrollment-assistant`):

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::YOUR_ACCOUNT_ID:oidc-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
           "StringLike": { "token.actions.githubusercontent.com:sub": "repo:YOUR_ORG/YOUR_REPO:*" }
         }
       }
     ]
   }
   ```

   - Attach a policy that allows ECR push (and optionally `ecr:GetAuthorizationToken`). Minimal policy:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": "ecr:GetAuthorizationToken",
         "Resource": "*"
       },
       {
         "Effect": "Allow",
         "Action": [
           "ecr:BatchCheckLayerAvailability",
           "ecr:GetDownloadUrlForLayer",
           "ecr:BatchGetImage",
           "ecr:PutImage",
           "ecr:InitiateLayerUpload",
           "ecr:UploadLayerPart",
           "ecr:CompleteLayerUpload"
         ],
         "Resource": [
           "arn:aws:ecr:us-west-2:YOUR_ACCOUNT_ID:repository/enrollment-assistant/agent-api",
           "arn:aws:ecr:us-west-2:YOUR_ACCOUNT_ID:repository/enrollment-assistant/rag-api"
         ]
       }
     ]
   }
   ```

3. **Add the role ARN** to GitHub secrets as `AWS_ROLE_ARN`.

### Option B: Static AWS keys

- Create an IAM user with programmatic access and the same ECR permissions as above.
- Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` to GitHub secrets.
- In `.github/workflows/deploy-aws.yml`, replace the “Configure AWS credentials” step with one that sets these env vars from secrets (and remove `role-to-assume`).

## 3. Enable EC2 deploy (optional)

1. **Repository variable:** Settings → Secrets and variables → Actions → Variables → New variable:  
   Name: `DEPLOY_TO_EC2`, Value: `true`.

2. **Secrets:** Set `EC2_HOST` (instance IP or hostname) and `EC2_SSH_PRIVATE_KEY` (full `.pem` contents).

3. **EC2 instance:** Must have AWS CLI configured (or an instance profile with `AmazonEC2ContainerRegistryReadOnly`) so the deploy script can run `aws ecr get-login-password` and `docker compose pull` for your ECR registry.

4. **Compose file:** The instance should already have `/opt/enrollment-assistant/docker-compose.ec2-rds.yml` (or `.ec2.yml`) and `.env` as in the [AWS deployment guide](AWS_DEPLOYMENT.md). The workflow sets `IMAGE_TAG` to the Git short SHA so the new images are pulled and used.

5. **GitHub environment (optional):** The deploy job uses `environment: production`. In Settings → Environments, add a “production” environment, or remove the `environment: production` line from the deploy job in `deploy-aws.yml`.

## 4. CI (tests)

- **Secrets (optional for CI):** If integration or E2E tests call external APIs, add `OPENAI_API_KEY` (and any others) to GitHub secrets and reference them in `ci.yml` as `secrets.OPENAI_API_KEY`.
- The existing `ci.yml` runs unit tests, integration tests (with Postgres service), and lint. Adjust branches and jobs in `.github/workflows/ci.yml` as needed.

## 5. Manual deploy

- **Trigger CD manually:** Actions → “Deploy to AWS” → Run workflow. You can optionally pass an input tag for the image version.
- **Deploy from your machine:** From repo root, `./scripts/deploy/aws-push-images.sh`, then SSH to EC2 and run `docker compose -f docker-compose.ec2-rds.yml pull && docker compose -f docker-compose.ec2-rds.yml up -d` (see [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)).
