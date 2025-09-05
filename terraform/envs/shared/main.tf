data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  secret_wildcard_arn = "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:${var.secret_name_prefix}*"

  bedrock_model_arns = [
    for id in var.bedrock_allowed_model_ids :
    "arn:aws:bedrock:${var.aws_region}::foundation-model/${id}"
  ]
}

# -------------------------
# Networking: SG + VPC Connector
# -------------------------

resource "aws_security_group" "connector" {
  name        = "origin-insights-llm-connector-sg"
  description = "Egress SG for App Runner VPC connector" # igual que el existente
  vpc_id      = var.vpc_id

  # Egress abierto (salida a NAT/Internet y Aurora)
  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = []
  }

  tags = merge(var.tags, {
    Name = "origin-insights-llm-connector-sg"
  })
}


# Permitir que el SG de Aurora reciba 5432 desde el SG del conector

resource "aws_security_group_rule" "aurora_ingress_from_connector" {
  count                    = var.create_aurora_ingress ? 1 : 0
  type                     = "ingress"
  description              = "App Runner connector - Aurora 5432"
  security_group_id        = var.aurora_sg_id
  source_security_group_id = aws_security_group.connector.id
  from_port                = 5432
  to_port                  = 5432
  protocol                 = "tcp"
}

resource "aws_apprunner_vpc_connector" "this" {
  vpc_connector_name = "origin-insights-llm-connector"
  subnets            = var.private_subnet_ids

  # Esto hace que coincida con el estado y no intente reemplazarlo.
  security_groups = [aws_security_group.connector.id]

  tags = var.tags

  # Opcional pero recomendable mientras hay servicios usando este conector
  lifecycle {
    prevent_destroy = true
  }
}


# -------------------------
# IAM: Instance Role (para el contenedor) + ECR Access Role
# -------------------------

# Trust policy: App Runner TAREAS (runtime)
data "aws_iam_policy_document" "instance_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["tasks.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "instance_role" {
  name               = var.instance_role_name
  assume_role_policy = data.aws_iam_policy_document.instance_assume.json
  tags               = var.tags
}

# Trust policy: App Runner BUILD (para extraer de ECR)
data "aws_iam_policy_document" "ecr_access_assume" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecr_access_role" {
  name               = var.ecr_access_role_name
  assume_role_policy = data.aws_iam_policy_document.ecr_access_assume.json
  tags               = var.tags
}

# --------- Policies vinculadas al Instance Role ---------

# 1) SecretsManager (lectura del secreto que rota con sufijo)
data "aws_iam_policy_document" "secrets_read" {
  statement {
    sid    = "ReadAuroraSecret"
    effect = "Allow"
    actions = [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ]
    resources = [local.secret_wildcard_arn]
  }
}

# 2) KMS decrypt sólo cuando el flujo es vía Secrets Manager
data "aws_iam_policy_document" "kms_decrypt" {
  statement {
    sid       = "KmsDecryptIfViaSecretsManager"
    effect    = "Allow"
    actions   = ["kms:Decrypt"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "kms:ViaService"
      values   = ["secretsmanager.${var.aws_region}.amazonaws.com"]
    }
  }
}

# 3) Bedrock (Invoke + Streaming). Para POC: '*' o restringido a modelos
data "aws_iam_policy_document" "bedrock_invoke" {
  statement {
    sid    = "BedrockInvoke"
    effect = "Allow"
    actions = [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
    ]
    resources = var.bedrock_lockdown ? local.bedrock_model_arns : ["*"]
  }
}

# 4) Bedrock KB (RAG). Para POC, '*' (evita errores por ARN exacto)
data "aws_iam_policy_document" "bedrock_kb" {
  statement {
    sid    = "BedrockKB"
    effect = "Allow"
    actions = [
      "bedrock:Retrieve",
      "bedrock:RetrieveAndGenerate"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "instance_inline" {
  name   = "origin-insights-llm-instance-inline"
  policy = data.aws_iam_policy_document.secrets_read.json
}

resource "aws_iam_policy" "kms_inline" {
  name   = "origin-insights-llm-kms-inline"
  policy = data.aws_iam_policy_document.kms_decrypt.json
}

resource "aws_iam_policy" "bedrock_invoke_inline" {
  name   = "origin-insights-llm-bedrock-invoke"
  policy = data.aws_iam_policy_document.bedrock_invoke.json
}

resource "aws_iam_policy" "bedrock_kb_inline" {
  name   = "origin-insights-llm-bedrock-kb"
  policy = data.aws_iam_policy_document.bedrock_kb.json
}

resource "aws_iam_role_policy_attachment" "attach_instance" {
  role       = aws_iam_role.instance_role.name
  policy_arn = aws_iam_policy.instance_inline.arn
}

resource "aws_iam_role_policy_attachment" "attach_kms" {
  role       = aws_iam_role.instance_role.name
  policy_arn = aws_iam_policy.kms_inline.arn
}

resource "aws_iam_role_policy_attachment" "attach_bedrock_invoke" {
  role       = aws_iam_role.instance_role.name
  policy_arn = aws_iam_policy.bedrock_invoke_inline.arn
}

resource "aws_iam_role_policy_attachment" "attach_bedrock_kb" {
  role       = aws_iam_role.instance_role.name
  policy_arn = aws_iam_policy.bedrock_kb_inline.arn
}

# --------- ECR access role (para que App Runner extraiga imagen) ---------

data "aws_iam_policy_document" "ecr_pull" {
  statement {
    effect = "Allow"
    actions = [
      "ecr:GetAuthorizationToken",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      "ecr:BatchCheckLayerAvailability",
      "ecr:DescribeImages",
      "ecr:DescribeRepositories"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "ecr_pull_inline" {
  name   = "origin-insights-llm-ecr-pull"
  policy = data.aws_iam_policy_document.ecr_pull.json
}

resource "aws_iam_role_policy_attachment" "attach_ecr_pull" {
  role       = aws_iam_role.ecr_access_role.name
  policy_arn = aws_iam_policy.ecr_pull_inline.arn
}