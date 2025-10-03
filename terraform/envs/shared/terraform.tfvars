aws_region = "us-east-1"

vpc_id = "vpc-0023ba7391440c4a6"

# Reemplaza por las subnets PRIVADAS
private_subnet_ids = [
  "subnet-0f91b801d9f8e68cf", # origin-insights-private-1a
  "subnet-0a7d395034c95b562", # origin-insights-private-1b
]

aurora_sg_id          = "sg-00863de208549fde5"
create_aurora_ingress = false

secret_name_prefix = "aurora-postgres-origin-insights-secret"

# POC: deja false para '*' (simple). Cuando se quiera bloquear por modelo, pasar a true
bedrock_lockdown = false

# Los dos modelos que soportaremos
bedrock_allowed_model_ids = [
  "anthropic.claude-3-5-haiku-20241022-v1:0",
  "anthropic.claude-3-7-sonnet-20250219-v1:0",
]

bedrock_default_model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
bedrock_smart_model_id   = "anthropic.claude-3-7-sonnet-20250219-v1:0"

bedrock_kb_id = "6RTOAOLLJG"