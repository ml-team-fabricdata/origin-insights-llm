variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "tf_state_bucket" {
  type    = string
  default = "infra-tf-origin-insights-llm"
}

variable "tf_lock_table" {
  type    = string
  default = "infra-tf-locks-origin-insights-llm"
}

variable "tf_state_prefix" {
  type    = string
  default = "origin-insights-llm"
}

variable "image_repo_uri" {
  type    = string
  default = "808571127262.dkr.ecr.us-east-1.amazonaws.com/origin-insights-llm"
}

variable "port" {
  type    = number
  default = 8080
}

variable "health_path" {
  type    = string
  default = "/healthz"
}

variable "allow_origins" {
  type    = string
  default = "*"
}

variable "offline_mode" {
  type    = string
  default = "0"
}

variable "debug_sess" {
  type    = string
  default = "1"
}

variable "aurora_secret_arn" {
  type    = string
  default = "arn:aws:secretsmanager:us-east-1:808571127262:secret:aurora-postgres-origin-insights-secret"
}

variable "aurora_secret_name" {
  type    = string
  default = "aurora-postgres-origin-insights-secret"
}

variable "tags" {
  type = map(string)
  default = {
    Project     = "origin-insights-llm"
    Environment = "services"
    IaC         = "terraform"
  }
}

# Nuevos tags en ECR
variable "tag_main" {
  type    = string
  default = "latest"
}

variable "tag_rg" {
  type    = string
  default = "latest"
}

variable "tag_er" {
  type    = string
  default = "latest"
}

variable "tag_ff" {
  type    = string
  default = "latest"
}