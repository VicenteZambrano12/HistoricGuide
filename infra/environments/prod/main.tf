terraform {
  required_version = "~> 1.13.5"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "8.5.0"
    }
  }
}

provider "google" {
  project                         = var.project_id
  region                          = var.region
  add_terraform_attribution_label = false
}

module "storage" {
  source     = "../../modules/storage"
  project_id = var.project_id
  region     = var.region
}

module "secrets" {
  source     = "../../modules/secrets"
  project_id = var.project_id
}

import {
  id = "historic-guide"
  to = module.storage.google_storage_bucket.app_data
}
