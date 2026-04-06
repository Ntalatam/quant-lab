# AWS Deployment

QuantLab now includes a production-oriented AWS deployment stack under `infra/aws/`. The design keeps the app interview-friendly and operationally coherent:

- CloudFront provides the single public URL.
- An ALB routes `/_next/*` and app traffic to the Next.js frontend service.
- The ALB routes `/api/*`, `/health`, `/docs`, `/redoc`, and `/openapi.json` to the FastAPI backend.
- ECS Fargate runs the frontend and backend as separate services.
- RDS PostgreSQL lives in private database subnets.
- Secrets Manager injects the backend `DATABASE_URL` and should also supply a strong `AUTH_SECRET_KEY`.

## Architecture

```text
CloudFront
  -> Application Load Balancer
    -> ECS Fargate frontend service (Next.js standalone)
    -> ECS Fargate backend service (FastAPI / Uvicorn)
  -> RDS PostgreSQL (private DB subnets)
```

The frontend should be deployed with `NEXT_PUBLIC_API_URL=/api`, so browser calls stay same-origin behind CloudFront.

## Prerequisites

- AWS account with permissions for VPC, ECS, ECR, ALB, CloudFront, Route53, RDS, IAM, CloudWatch, and Secrets Manager
- `terraform` 1.6+
- Docker
- AWS CLI configured
- Optional custom domain with:
  - Route53 hosted zone
  - ACM certificate in `us-east-1`

## Optional: Bootstrap Remote State

The main stack does not force a remote backend, but a bootstrap configuration is included for teams that want S3 state + DynamoDB locking.

```bash
cd infra/aws/bootstrap
terraform init
terraform apply \
  -var='aws_region=us-east-1' \
  -var='state_bucket_name=your-unique-quantlab-tf-state'
```

Copy the `backend_config_snippet` output into a local `backend.hcl` file and then initialize the main stack with it:

```bash
cd ../
terraform init -backend-config=backend.hcl
```

If you do not want remote state yet, run the main stack with local state instead.

## First-Time Deploy

1. Copy the example variables:

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
```

2. Edit `terraform.tfvars` with your domain, hosted zone, certificate ARN, and preferred image tags.

3. Create the ECR repositories used for the first image push:

```bash
terraform init
terraform apply \
  -target=aws_ecr_repository.frontend \
  -target=aws_ecr_repository.backend
```

4. Build and push the application images to the repository URLs output by Terraform. The frontend build must receive `NEXT_PUBLIC_API_URL=/api` at build time so browser requests stay same-origin behind CloudFront:

```bash
../../scripts/deploy/push-aws-images.sh \
  us-east-1 \
  <frontend_repo> \
  <backend_repo> \
  2026-04-04
```

5. Apply the full stack:

```bash
terraform apply
```

6. Verify:

- `terraform output app_url`
- `terraform output frontend_healthcheck_url`
- `terraform output backend_healthcheck_url`

## Runtime Notes

- Backend health path: `/health`
- Frontend health path: `/healthz`
- Backend docs: `/docs`
- Set `AUTH_COOKIE_SECURE=true` anywhere the app is served behind HTTPS.
- Frontend and backend share one public origin, so same-origin API calls work without a dedicated frontend proxy layer.
- The frontend image is built with `NEXT_PUBLIC_API_URL=/api`; changing the public API base requires rebuilding the frontend image.
- ECS services default to public subnets with public IPs to avoid NAT Gateway cost for a portfolio demo. Security groups still only allow ingress from the ALB.

## GitHub Actions Staging Deploy

Tier 4 adds a guarded staging workflow at `.github/workflows/deploy-staging.yml`. It triggers on pushes to `main` that affect the app, infra, or deployment scripts, and it will skip cleanly with a workflow summary if the repo is not configured for AWS yet.

Required GitHub secrets:

- `AWS_GITHUB_DEPLOY_ROLE_ARN`: IAM role assumed through GitHub OIDC for ECR + Terraform access
- `TF_BACKEND_CONFIG`: multi-line Terraform backend config snippet (for example the S3 bucket / DynamoDB settings from the bootstrap stack)

Required GitHub repository variables:

- `AWS_ECR_FRONTEND_REPOSITORY_URL`
- `AWS_ECR_BACKEND_REPOSITORY_URL`

Optional GitHub repository variables:

- `AWS_REGION` default: `us-east-1`
- `TF_VAR_project_name` default: `quantlab`
- `TF_VAR_environment` default: `staging`
- `TF_VAR_domain_name`
- `TF_VAR_hosted_zone_id`
- `TF_VAR_acm_certificate_arn`
- `TF_VAR_database_username` default: `quantlab`

The workflow builds and pushes frontend/backend images tagged with `github.sha`, applies the Terraform stack in `infra/aws`, and verifies the deployed `/healthz` and `/health` endpoints from Terraform outputs. The first deploy still assumes the ECR repositories and Terraform backend already exist, so do the bootstrap and first-time infra setup once before relying on automated staging deploys.

## Operational Recommendations

- Enable `enable_deletion_protection=true` before treating the database as persistent.
- Replace the demo-sized `db.t4g.micro` once you expect heavier load.
- Add AWS WAF in front of CloudFront if you want rate limiting / bot filtering.
- If you add GitHub-based deployment automation later, wire it to the ECR outputs from this stack rather than hardcoding repository names.
