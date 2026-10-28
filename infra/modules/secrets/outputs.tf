output "secret_id" {
  description = "Secret ID; no secret version or payload is managed."
  value       = google_secret_manager_secret.app_secrets.secret_id
}

output "secret_name" {
  description = "Fully qualified global Secret Manager resource name."
  value       = google_secret_manager_secret.app_secrets.name
}
