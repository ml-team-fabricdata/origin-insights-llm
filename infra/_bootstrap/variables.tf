variable "aws_region" {
  type        = string
  description = "AWS region"
  default     = "us-east-1"
}

variable "state_bucket_name" {
  type        = string
  description = "S3 bucket name for Terraform remote state (global unique)"
  default     = "infra-tf-origin-insights-llm"
}

variable "lock_table_name" {
  type        = string
  description = "DynamoDB table name for Terraform state locking"
  default     = "infra-tf-locks-origin-insights-llm"
}

variable "tags" {
  type        = map(string)
  description = "Common tags"
  default = {
    Project     = "origin-insights-llm"
    IaC         = "terraform"
    Environment = "shared"
  }
}