locals {
  shared   = data.terraform_remote_state.shared.outputs
  repo_uri = var.image_repo_uri # <- SIN tag, solo el repo: 8085....amazonaws.com/origin-insights-llm
  base_env = {
    PORT                     = tostring(var.port)
    ALLOW_ORIGINS            = var.allow_origins
    OFFLINE_MODE             = var.offline_mode
    DEBUG_SESS               = var.debug_sess
    AURORA_SECRET_ARN        = var.aurora_secret_arn
    AURORA_SECRET_NAME       = var.aurora_secret_name
    BEDROCK_DEFAULT_MODEL_ID = local.shared.bedrock_default_model_id
    BEDROCK_SMART_MODEL_ID   = local.shared.bedrock_smart_model_id
    BEDROCK_KB_ID            = local.shared.bedrock_kb_id
    AWS_REGION               = var.aws_region
  }
}

module "apprunner_main" {
  source = "../../modules/apprunner_service"

  service_name             = "origin-insights-llm-main"
  image_identifier         = "${local.repo_uri}:main"
  port                     = var.port
  health_path              = var.health_path
  access_role_arn          = local.shared.ecr_access_role_arn
  instance_role_arn        = local.shared.instance_role_arn
  vpc_connector_arn        = local.shared.apprunner_vpc_connector_arn
  auto_deployments_enabled = true
  env                      = merge(local.base_env, { APP_ENV = "main" })
  tags                     = merge(var.tags, { Environment = "main" })
}

module "apprunner_rafa" {
  source = "../../modules/apprunner_service"

  service_name             = "origin-insights-llm-rafa"
  image_identifier         = "${local.repo_uri}:rg"
  port                     = var.port
  health_path              = var.health_path   # / en caso de que /healthz no exista
  access_role_arn          = local.shared.ecr_access_role_arn
  instance_role_arn        = local.shared.instance_role_arn
  vpc_connector_arn        = local.shared.apprunner_vpc_connector_arn
  auto_deployments_enabled = true
  env                      = merge(local.base_env, { APP_ENV = "rafa" })
  tags                     = merge(var.tags, { Environment = "rafa" })
}

module "apprunner_ele" {
  source = "../../modules/apprunner_service"

  service_name             = "origin-insights-llm-ele"
  image_identifier         = "${local.repo_uri}:er"
  port                     = var.port
  health_path              = var.health_path
  access_role_arn          = local.shared.ecr_access_role_arn
  instance_role_arn        = local.shared.instance_role_arn
  vpc_connector_arn        = local.shared.apprunner_vpc_connector_arn
  auto_deployments_enabled = true
  env                      = merge(local.base_env, { APP_ENV = "rafa" })
  tags                     = merge(var.tags, { Environment = "ele" })
}

module "apprunner_fran" {
  source = "../../modules/apprunner_service"

  service_name             = "origin-insights-llm-fran"
  image_identifier         = "${local.repo_uri}:ff"
  port                     = var.port
  health_path              = var.health_path
  access_role_arn          = local.shared.ecr_access_role_arn
  instance_role_arn        = local.shared.instance_role_arn
  vpc_connector_arn        = local.shared.apprunner_vpc_connector_arn
  auto_deployments_enabled = true
  env                      = merge(local.base_env, { APP_ENV = "fran" })
  tags                     = merge(var.tags, { Environment = "fran" })
}