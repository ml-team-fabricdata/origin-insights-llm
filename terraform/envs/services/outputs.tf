output "main_url" { value = module.apprunner_main.service_url }
output "rafa_url" { value = module.apprunner_rafa.service_url }
output "ele_url" { value = module.apprunner_ele.service_url }
output "fran_url" { value = module.apprunner_fran.service_url }

output "main_arn" { value = module.apprunner_main.service_arn }
output "rafa_arn" { value = module.apprunner_rafa.service_arn }
output "ele_arn" { value = module.apprunner_ele.service_arn }
output "fran_arn" { value = module.apprunner_fran.service_arn }