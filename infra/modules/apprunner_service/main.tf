resource "aws_apprunner_service" "this" {
  service_name = var.service_name
  
  source_configuration {
    authentication_configuration {
      access_role_arn = var.access_role_arn
    }
    auto_deployments_enabled = var.auto_deployments_enabled

    image_repository {
      image_identifier      = var.image_identifier
      image_repository_type = "ECR"

      image_configuration {
        port = tostring(var.port)
        runtime_environment_variables = var.env
      }
    }
  }

  # Usar UNO de estos estilos. Se deja el legible.
  instance_configuration {
    cpu               = "1 vCPU"  # o "1024"
    memory            = "2 GB"    # o "2048"
    instance_role_arn = var.instance_role_arn
  }

  # Mantener el health check si la app expone /healthz
  health_check_configuration {
    protocol            = "HTTP"
    path                = var.health_path
    healthy_threshold   = 1
    unhealthy_threshold = 5
    interval            = 10
    timeout             = 5
  }

  network_configuration {
    egress_configuration {
      egress_type       = "VPC"
      vpc_connector_arn = var.vpc_connector_arn
    }
  }

  tags = var.tags
}