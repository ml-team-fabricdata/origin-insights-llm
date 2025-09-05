variable "service_name" {
  type = string
}

variable "image_identifier" {
  type        = string
  description = "ECR image ref completo, p.ej: 8085....amazonaws.com/origin-insights-llm:main"
}

variable "port" {
  type    = number
  default = 8080
}

variable "health_path" {
  type    = string
  default = "/healthz"
}

variable "access_role_arn" {
  type = string
}

variable "instance_role_arn" {
  type = string
}

variable "vpc_connector_arn" {
  type = string
}

variable "env" {
  type    = map(string)
  default = {}
}

variable "tags" {
  type    = map(string)
  default = {}
}

variable "auto_deployments_enabled" {
  type    = bool
  default = true
}