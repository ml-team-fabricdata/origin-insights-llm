output "connector_security_group_id" {
  value = aws_security_group.connector.id
}

output "apprunner_vpc_connector_arn" {
  value = aws_apprunner_vpc_connector.this.arn
}

output "instance_role_arn" {
  value = aws_iam_role.instance_role.arn
}

output "ecr_access_role_arn" {
  value = aws_iam_role.ecr_access_role.arn
}

output "bedrock_default_model_id" {
  value = var.bedrock_default_model_id
}

output "bedrock_smart_model_id" {
  value = var.bedrock_smart_model_id
}

output "bedrock_kb_id" {
  value = var.bedrock_kb_id
}