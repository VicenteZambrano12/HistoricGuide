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

module "cloudrun" {
  source                = "../../modules/cloudrun"
  project_id            = var.project_id
  region                = var.region
  app_container_image   = var.app_container_image
  service_account_email = "historicguide@basicrahgapp.iam.gserviceaccount.com"
  secret_id             = module.secrets.secret_id
  serverless_subnet_id  = "projects/${var.project_id}/regions/${var.region}/subnetworks/serverless-egress-subnet"
  qdrant_internal_ip    = "10.0.1.2"
  environment           = var.environment
}

module "logging" {
  source                = "../../modules/logging"
  project_id            = var.project_id
  region                = var.region
  environment           = var.environment
  service_name          = "historicguide-backend"
  bucket_id             = var.log_bucket_id
  retention_days        = var.log_retention_days
  error_threshold_count = var.log_error_threshold_count
  notification_channels = var.log_notification_channels
}

import {
  id = "historic-guide"
  to = module.storage.google_storage_bucket.app_data
}

import {
  id = "projects/basicrahgapp/locations/europe-southwest1/repositories/historicguide-repo"
  to = module.artifact_registry.google_artifact_registry_repository.default
}
