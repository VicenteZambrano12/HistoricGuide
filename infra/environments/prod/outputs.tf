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

output "artifact_registry_image" {
  description = "Application image base; workflow tags it by commit and resolves its digest."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${module.artifact_registry.repository_id}/historicguide"
}
