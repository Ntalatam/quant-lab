locals {
  name_prefix = "${var.project_name}-${var.environment}"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Repository  = "quant-lab"
    },
    var.tags,
  )

  frontend_image_uri = var.frontend_image != "" ? var.frontend_image : "${aws_ecr_repository.frontend.repository_url}:${var.frontend_image_tag}"
  backend_image_uri  = var.backend_image != "" ? var.backend_image : "${aws_ecr_repository.backend.repository_url}:${var.backend_image_tag}"

  public_app_url = var.domain_name != "" ? "https://${var.domain_name}" : "https://${aws_cloudfront_distribution.app.domain_name}"

  backend_cors_origins = var.domain_name != "" ? ["https://${var.domain_name}"] : []
}
