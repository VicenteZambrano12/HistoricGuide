resource "google_storage_bucket" "app_data" {
  project                     = var.project_id
  name                        = "historic-guide"
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false

  encryption {
    customer_managed_encryption_enforcement_config {
      restriction_mode = "NotRestricted"
    }
    customer_supplied_encryption_enforcement_config {
      restriction_mode = "FullyRestricted"
    }
    google_managed_encryption_enforcement_config {
      restriction_mode = "NotRestricted"
    }
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  lifecycle {
    prevent_destroy = true
  }
}
