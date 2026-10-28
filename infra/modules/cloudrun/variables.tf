variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "serverless_subnet_id" {
  type = string
}

variable "qdrant_internal_ip" {
  type = string
}

variable "app_container_image" {
  type        = string
  description = "Immutable digest published by the deployment workflow."

  validation {
    condition     = can(regex("^europe-southwest1-docker\\.pkg\\.dev/basicrahgapp/historicguide-repo/historicguide@sha256:[0-9a-f]{64}$", var.app_container_image))
    error_message = "Use an immutable digest from the dedicated HistoricGuide image package."
  }
}

variable "service_account_email" {
  type        = string
  description = "Existing runtime service account for the Cloud Run service."
}

variable "secret_id" {
  type        = string
  description = "Secret Manager secret id holding the app secrets JSON blob."
}
