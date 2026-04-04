# AWS Terraform Stack

This directory contains the AWS deployment stack for QuantLab:

- `network.tf`: VPC, public ECS subnets, and private database subnets
- `security.tf`: ALB, ECS service, and RDS security groups
- `database.tf`: PostgreSQL RDS instance plus Secrets Manager `DATABASE_URL`
- `ecr.tf`: frontend and backend ECR repositories
- `ecs.tf`: ECS cluster, task definitions, and services
- `alb.tf`: Application Load Balancer and path routing
- `cloudfront.tf`: single public edge URL with static asset caching

Detailed deployment instructions live in `docs/deployment/aws-ecs.md`.
