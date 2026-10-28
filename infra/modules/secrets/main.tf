resource "google_secret_manager_secret" "app_secrets" {
  secret_id = "basicragapp-secrets"
  labels    = merge(var.common_labels, { component = "secrets" })

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "cloud_run_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.app_secrets.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${var.cloud_run_service_account_email}"
}
