output "bucket_name" {
  description = "Full name of the private Cloud Logging bucket."
  value       = google_logging_project_bucket_config.application.id
}

output "service_filter" {
  description = "Logs Explorer filter for backend and frontend hosting logs."
  value       = local.service_filter
}

output "error_metric_type" {
  description = "Monitoring metric type counting error log entries."
  value       = "logging.googleapis.com/user/${google_logging_metric.errors.name}"
}

output "alert_policy_name" {
  description = "Monitoring incident policy; notification channels are configured separately."
  value       = google_monitoring_alert_policy.errors.name
}
