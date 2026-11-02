output "bucket_name" {
  description = "Existing bucket now tracked in the HistoricGuide state."
  value       = module.storage.bucket_name
}

output "secret_id" {
  description = "Application secret containing the runtime JSON configuration."
  value       = module.secrets.secret_id
}

output "cloud_run_url" {
  description = "Public frontend URL; API routes are under /api."
  value       = module.cloudrun.cloud_run_url
}

output "secret_name" {
  description = "Global Secret Manager resource; this stage creates no versions."
  value       = module.secrets.secret_name
}

output "artifact_registry_image" {
  description = "Application image base; workflow tags it by commit and resolves its digest."
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${module.artifact_registry.repository_id}/historicguide"
}

output "logging_bucket_name" {
  description = "Centralized structured application and frontend/API access log bucket."
  value       = module.logging.bucket_name
}

output "logging_service_filter" {
  description = "Service-only filter to use with the logging bucket in Logs Explorer."
  value       = module.logging.service_filter
}

output "logging_error_metric_type" {
  value = module.logging.error_metric_type
}

output "logging_alert_policy_name" {
  value = module.logging.alert_policy_name
}
