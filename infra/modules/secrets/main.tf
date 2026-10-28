resource "google_secret_manager_secret" "app_secrets" {
  project   = var.project_id
  secret_id = "historicguide-secrets"

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}
