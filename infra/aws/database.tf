resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnets"
  subnet_ids = [for subnet in aws_subnet.database : subnet.id]

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-db-subnet-group"
  })
}

resource "random_password" "database" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_db_instance" "postgres" {
  identifier                   = "${local.name_prefix}-postgres"
  engine                       = "postgres"
  engine_version               = "15.8"
  instance_class               = var.database_instance_class
  allocated_storage            = var.database_allocated_storage
  max_allocated_storage        = var.database_max_allocated_storage
  db_name                      = var.database_name
  username                     = var.database_username
  password                     = random_password.database.result
  port                         = 5432
  db_subnet_group_name         = aws_db_subnet_group.main.name
  vpc_security_group_ids       = [aws_security_group.database.id]
  backup_retention_period      = var.database_backup_retention_days
  deletion_protection          = var.enable_deletion_protection
  skip_final_snapshot          = var.database_skip_final_snapshot
  publicly_accessible          = false
  storage_encrypted            = true
  auto_minor_version_upgrade   = true
  multi_az                     = false
  performance_insights_enabled = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-postgres"
  })
}

resource "aws_secretsmanager_secret" "backend_database_url" {
  name        = "${local.name_prefix}/backend/database-url"
  description = "Async SQLAlchemy connection string for the QuantLab backend."

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-backend-database-url"
  })
}

resource "aws_secretsmanager_secret_version" "backend_database_url" {
  secret_id = aws_secretsmanager_secret.backend_database_url.id
  secret_string = format(
    "postgresql+asyncpg://%s:%s@%s:%d/%s",
    var.database_username,
    random_password.database.result,
    aws_db_instance.postgres.address,
    5432,
    var.database_name,
  )
}
