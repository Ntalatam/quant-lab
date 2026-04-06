variable "aws_region" {
  description = "AWS region used for the deployment."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Short project slug used in AWS resource names."
  type        = string
  default     = "quantlab"
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "production"
}

variable "availability_zones" {
  description = "Availability zones used for public ECS subnets and private database subnets."
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "Provide at least two availability zones for the AWS deployment."
  }
}

variable "vpc_cidr" {
  description = "CIDR range for the VPC."
  type        = string
  default     = "10.42.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for ECS / ALB public subnets."
  type        = list(string)
  default     = ["10.42.0.0/20", "10.42.16.0/20"]

  validation {
    condition     = length(var.public_subnet_cidrs) == length(var.availability_zones)
    error_message = "public_subnet_cidrs must have one CIDR block per availability zone."
  }
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for private database subnets."
  type        = list(string)
  default     = ["10.42.128.0/20", "10.42.144.0/20"]

  validation {
    condition     = length(var.database_subnet_cidrs) == length(var.availability_zones)
    error_message = "database_subnet_cidrs must have one CIDR block per availability zone."
  }
}

variable "ecs_assign_public_ip" {
  description = "Whether ECS tasks receive public IPs. True avoids NAT Gateway cost for a demo environment."
  type        = bool
  default     = true
}

variable "frontend_container_port" {
  description = "Port exposed by the frontend container."
  type        = number
  default     = 3000
}

variable "backend_container_port" {
  description = "Port exposed by the backend container."
  type        = number
  default     = 8000
}

variable "frontend_cpu" {
  description = "Fargate CPU units for the frontend task."
  type        = number
  default     = 1024
}

variable "frontend_memory" {
  description = "Fargate memory (MiB) for the frontend task."
  type        = number
  default     = 2048
}

variable "backend_cpu" {
  description = "Fargate CPU units for the backend task."
  type        = number
  default     = 1024
}

variable "backend_memory" {
  description = "Fargate memory (MiB) for the backend task."
  type        = number
  default     = 2048
}

variable "worker_cpu" {
  description = "Fargate CPU units for the worker task."
  type        = number
  default     = 1024
}

variable "worker_memory" {
  description = "Fargate memory (MiB) for the worker task."
  type        = number
  default     = 2048
}

variable "frontend_desired_count" {
  description = "Desired number of running frontend tasks."
  type        = number
  default     = 1
}

variable "backend_desired_count" {
  description = "Desired number of running backend tasks."
  type        = number
  default     = 1
}

variable "worker_desired_count" {
  description = "Desired number of running worker tasks."
  type        = number
  default     = 1
}

variable "frontend_health_check_path" {
  description = "Application path used by the ALB to check frontend health."
  type        = string
  default     = "/healthz"
}

variable "backend_health_check_path" {
  description = "Application path used by the ALB to check backend health."
  type        = string
  default     = "/health"
}

variable "frontend_next_public_api_url" {
  description = "Public API base injected into the frontend container."
  type        = string
  default     = "/api"

  validation {
    condition = (
      startswith(var.frontend_next_public_api_url, "/") ||
      startswith(var.frontend_next_public_api_url, "http://") ||
      startswith(var.frontend_next_public_api_url, "https://")
    )
    error_message = "frontend_next_public_api_url must be a relative path or an absolute HTTP(S) URL."
  }
}

variable "database_name" {
  description = "Primary application database name."
  type        = string
  default     = "quantlab"
}

variable "database_username" {
  description = "Primary database username."
  type        = string
  default     = "quantlab"
}

variable "database_instance_class" {
  description = "RDS instance class."
  type        = string
  default     = "db.t4g.micro"
}

variable "database_allocated_storage" {
  description = "Initial database storage in GiB."
  type        = number
  default     = 20
}

variable "database_max_allocated_storage" {
  description = "Maximum storage autoscaling ceiling in GiB."
  type        = number
  default     = 100
}

variable "database_backup_retention_days" {
  description = "Number of days to retain automated RDS backups."
  type        = number
  default     = 7
}

variable "database_skip_final_snapshot" {
  description = "Whether RDS skips a final snapshot on destroy."
  type        = bool
  default     = true
}

variable "enable_deletion_protection" {
  description = "Whether to enable deletion protection on the RDS instance."
  type        = bool
  default     = false
}

variable "frontend_image" {
  description = "Optional full image URI for the frontend container. Defaults to the managed ECR repo plus image tag."
  type        = string
  default     = ""
}

variable "backend_image" {
  description = "Optional full image URI for the backend container. Defaults to the managed ECR repo plus image tag."
  type        = string
  default     = ""
}

variable "frontend_image_tag" {
  description = "Frontend image tag used when frontend_image is not provided."
  type        = string
  default     = "latest"
}

variable "backend_image_tag" {
  description = "Backend image tag used when backend_image is not provided."
  type        = string
  default     = "latest"
}

variable "domain_name" {
  description = "Optional vanity domain to attach to CloudFront."
  type        = string
  default     = ""
}

variable "hosted_zone_id" {
  description = "Optional Route53 hosted zone ID used when domain_name is configured."
  type        = string
  default     = ""

  validation {
    condition     = var.hosted_zone_id == "" || var.domain_name != ""
    error_message = "hosted_zone_id can only be set when domain_name is configured."
  }
}

variable "acm_certificate_arn" {
  description = "Optional us-east-1 ACM certificate ARN for the vanity domain."
  type        = string
  default     = ""

  validation {
    condition     = var.acm_certificate_arn == "" || var.domain_name != ""
    error_message = "domain_name must be set when acm_certificate_arn is provided."
  }
}

variable "cloudfront_price_class" {
  description = "CloudFront price class."
  type        = string
  default     = "PriceClass_100"
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days."
  type        = number
  default     = 30
}

variable "tags" {
  description = "Additional tags applied to all supported resources."
  type        = map(string)
  default     = {}
}
