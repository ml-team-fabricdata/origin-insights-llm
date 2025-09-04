# envs/services/data_shared.tf
data "terraform_remote_state" "shared" {
  backend = "s3"
  config = {
    bucket  = var.tf_state_bucket
    key     = "${var.tf_state_prefix}/envs/shared/terraform.tfstate"
    region  = var.aws_region
    encrypt = true
  }
}