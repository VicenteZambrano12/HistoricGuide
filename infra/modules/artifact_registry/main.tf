resource "google_artifact_registry_repository" "default" {
  project                = var.project_id
  location               = var.location
  repository_id          = var.repository_id
  format                 = "DOCKER"
  description            = "HistoricGuide Docker images managed by Terraform"
  cleanup_policy_dry_run = false

  cleanup_policies {
    id     = "keep-last-2-historicguide"
    action = "KEEP"

    most_recent_versions {
      keep_count            = 2
      package_name_prefixes = ["historicguide"]
    }
  }

  cleanup_policies {
    id     = "delete-old-historicguide"
    action = "DELETE"

    condition {
      tag_state             = "ANY"
      package_name_prefixes = ["historicguide"]
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}