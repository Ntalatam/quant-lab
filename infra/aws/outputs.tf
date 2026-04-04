output "frontend_ecr_repository_url" {
  description = "ECR repository URL for the frontend image."
  value       = aws_ecr_repository.frontend.repository_url
}

output "backend_ecr_repository_url" {
  description = "ECR repository URL for the backend image."
  value       = aws_ecr_repository.backend.repository_url
}

output "frontend_healthcheck_url" {
  description = "Public frontend health endpoint."
  value       = "${local.public_app_url}${var.frontend_health_check_path}"
}

output "backend_healthcheck_url" {
  description = "Public backend health endpoint."
  value       = "${local.public_app_url}${var.backend_health_check_path}"
}

output "alb_dns_name" {
  description = "Public ALB DNS name."
  value       = aws_lb.app.dns_name
}

output "cloudfront_domain_name" {
  description = "CloudFront distribution domain name."
  value       = aws_cloudfront_distribution.app.domain_name
}

output "app_url" {
  description = "Primary public URL for the deployed application."
  value       = local.public_app_url
}

output "database_address" {
  description = "RDS endpoint hostname."
  value       = aws_db_instance.postgres.address
}

output "backend_database_url_secret_arn" {
  description = "Secrets Manager ARN containing the backend DATABASE_URL."
  value       = aws_secretsmanager_secret.backend_database_url.arn
}
