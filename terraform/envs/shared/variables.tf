variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_id" {
  type        = string
  description = "VPC donde vive Aurora y donde se creará el VPC Connector"
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "Subnets PRIVADAS para el App Runner VPC Connector (ej. 1a y 1b)"
}

variable "aurora_sg_id" {
  type        = string
  description = "Security Group del clúster Aurora"
}

variable "connector_sg_name" {
  type    = string
  default = "origin-insights-llm-connector-sg"
}

variable "apprunner_vpc_connector_name" {
  type    = string
  default = "origin-insights-llm-connector"
}

variable "secret_name_prefix" {
  type        = string
  default     = "aurora-postgres-origin-insights-secret"
  description = "Prefijo del secreto (cubre sufijos rotados con wildcard)"
}

variable "enable_bedrock_permissions" {
  type    = bool
  default = true
}

# Permitir ambos modelos: Haiku (rápido) y Sonnet 3.7 (smart)
variable "bedrock_allowed_model_ids" {
  type = list(string)
  default = [
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
  ]
}

# Defaults para routing
variable "bedrock_default_model_id" {
  type    = string
  default = "anthropic.claude-3-5-haiku-20241022-v1:0"
}

variable "bedrock_smart_model_id" {
  type    = string
  default = "anthropic.claude-3-7-sonnet-20250219-v1:0"
}

variable "bedrock_kb_id" {
  type    = string
  default = "6RTOAOLLJG"
}

# Si se quiere bloquear por modelo exacto, se coloca true. Para POC, false = '*'
variable "bedrock_lockdown" {
  type    = bool
  default = false
}

# (opcional) evitar colisiones con roles ya existentes
variable "instance_role_name" {
  type    = string
  default = "origin-insights-llm-instance-role-tf"
}

variable "ecr_access_role_name" {
  type    = string
  default = "origin-insights-llm-ecr-access-role-tf"
}

variable "tags" {
  type = map(string)
  default = {
    Project     = "origin-insights-llm"
    Environment = "shared"
    IaC         = "terraform"
  }
}

variable "create_aurora_ingress" {
  type    = bool
  default = false
}