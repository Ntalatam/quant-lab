resource "aws_security_group" "alb" {
  name        = "${local.name_prefix}-alb"
  description = "Public ingress for the QuantLab application load balancer."
  vpc_id      = aws_vpc.main.id

  ingress {
    description      = "Public HTTP entrypoint"
    from_port        = 80
    to_port          = 80
    protocol         = "tcp"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  egress {
    description = "Forward traffic to ECS services"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb-sg"
  })
}

resource "aws_security_group" "frontend_service" {
  name        = "${local.name_prefix}-frontend"
  description = "Ingress to the frontend ECS service from the ALB."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "ALB to frontend"
    from_port       = var.frontend_container_port
    to_port         = var.frontend_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-frontend-sg"
  })
}

resource "aws_security_group" "backend_service" {
  name        = "${local.name_prefix}-backend"
  description = "Ingress to the backend ECS service from the ALB."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "ALB to backend"
    from_port       = var.backend_container_port
    to_port         = var.backend_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backend-sg"
  })
}

resource "aws_security_group" "database" {
  name        = "${local.name_prefix}-database"
  description = "Postgres ingress from the backend ECS service."
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Backend to Postgres"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.backend_service.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-database-sg"
  })
}
