variable "project_id" {
  type        = string
  description = "Project containing the existing HistoricGuide bucket."

  validation {
    condition     = var.project_id == "basicrahgapp"
    error_message = "This import must use the existing basicrahgapp project."
  }

}

variable "app_container_image" {
  type        = string
  description = "Immutable HistoricGuide image digest resolved by the existing workflow."

  validation {
    condition     = can(regex("^europe-southwest1-docker\\.pkg\\.dev/basicrahgapp/historicguide-repo/historicguide@sha256:[0-9a-f]{64}$", var.app_container_image))
    error_message = "The application image must be an immutable digest in historicguide-repo/historicguide."
  }
}

variable "region" {
  type        = string
  description = "Existing bucket region; changing this would require replacement."

  validation {
    condition     = var.region == "europe-southwest1"
    error_message = "The existing bucket is in europe-southwest1."
  }
}
