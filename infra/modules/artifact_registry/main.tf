resource "google_artifact_registry_repository" "default" {
  project                = var.project_id
  location               = var.location
  repository_id          = var.repository_id
  format                 = "DOCKER"
  description            = "Repositorio Docker principal gestionado por Terraform"
  cleanup_policy_dry_run = false
  labels                 = merge(var.common_labels, { component = "artifact-registry" })

  cleanup_policies {
    id     = "keep-last-2-basicragapp"
    action = "KEEP"

    most_recent_versions {
      keep_count            = 2
      package_name_prefixes = ["basicragapp"]
    }
  }

  cleanup_policies {
    id     = "delete-old-basicragapp"
    action = "DELETE"

    condition {
      tag_state             = "ANY"
      package_name_prefixes = ["basicragapp"]
    }
  }
}