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

module "artifact_registry" {
  source        = "../../modules/artifact_registry"
  project_id    = var.project_id
  location      = var.region
  repository_id = "historicguide-repo"
}

import {
  id = "historic-guide"
  to = module.storage.google_storage_bucket.app_data
}

import {
  id = "projects/basicrahgapp/locations/europe-southwest1/repositories/historicguide-repo"
  to = module.artifact_registry.google_artifact_registry_repository.default
}
