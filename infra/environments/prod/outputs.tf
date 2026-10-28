output "bucket_name" {
  description = "Existing bucket now tracked in the HistoricGuide state."
  value       = module.storage.bucket_name
}

output "secret_id" {
  description = "Empty application secret reserved for a future JSON payload."
  value       = module.secrets.secret_id
}

output "secret_name" {
  description = "Global Secret Manager resource; this stage creates no versions."
  value       = module.secrets.secret_name
}
