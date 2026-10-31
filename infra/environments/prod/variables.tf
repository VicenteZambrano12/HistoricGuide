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

variable "environment" {
  type        = string
  description = "This root/state is production only; use a separate root/state for dev."
  default     = "prod"

  validation {
    condition     = var.environment == "prod"
    error_message = "Do not deploy dev resources into the production state."
  }
}

variable "log_bucket_id" {
  type        = string
  description = "Environment-specific centralized bucket for this combined frontend/API service."
  default     = "historicguide-prod-logs"

  validation {
    condition     = can(regex("^historicguide-prod-[a-z0-9-]+$", var.log_bucket_id))
    error_message = "The production log bucket must use the historicguide-prod- prefix."
  }
}

variable "log_retention_days" {
  type        = number
  description = "Retention for new logs routed to the dedicated bucket."
  default     = 30

  validation {
    condition     = contains([14, 30], var.log_retention_days)
    error_message = "Log retention must be 14 or 30 days."
  }
}

variable "log_error_threshold_count" {
  type        = number
  description = "Error log entries in five minutes needed to open an incident."
  default     = 5

  validation {
    condition     = var.log_error_threshold_count >= 1 && var.log_error_threshold_count <= 1000 && floor(var.log_error_threshold_count) == var.log_error_threshold_count
    error_message = "The error threshold must be an integer from 1 to 1000."
  }
}

variable "log_notification_channels" {
  type        = list(string)
  description = "Existing project notification channels; empty means console incidents only."
  default     = []

  validation {
    condition     = alltrue([for channel in var.log_notification_channels : can(regex("^projects/${var.project_id}/notificationChannels/[0-9]+$", channel))])
    error_message = "Use existing notification channel resource names in basicrahgapp."
  }
}
