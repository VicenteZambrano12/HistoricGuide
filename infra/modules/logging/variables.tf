variable "project_id" {
  type        = string
  description = "Project hosting both the Cloud Run service and its log bucket."
}

variable "region" {
  type        = string
  description = "Regional Cloud Run service and log storage location."
}

variable "environment" {
  type        = string
  description = "Environment used in descriptions and Monitoring labels."

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "Use dev or prod for the logging environment."
  }
}

variable "service_name" {
  type        = string
  description = "Exact Cloud Run service to collect; no other services are routed."
}

variable "bucket_id" {
  type        = string
  description = "Environment-specific Cloud Logging bucket ID, not a Cloud Storage bucket."

  validation {
    condition     = can(regex("^historicguide-${var.environment}-[a-z0-9-]+$", var.bucket_id))
    error_message = "The bucket ID must start with historicguide- followed by the configured environment."
  }
}

variable "retention_days" {
  type        = number
  description = "Approved log retention: 14 or 30 days."
  default     = 30

  validation {
    condition     = contains([14, 30], var.retention_days)
    error_message = "Log retention must be 14 or 30 days."
  }
}

variable "error_threshold_count" {
  type        = number
  description = "Minimum ERROR/5xx log-entry count within five minutes to open an incident."
  default     = 5

  validation {
    condition     = var.error_threshold_count >= 1 && var.error_threshold_count <= 1000 && floor(var.error_threshold_count) == var.error_threshold_count
    error_message = "The error threshold must be an integer from 1 to 1000."
  }
}

variable "notification_channels" {
  type        = list(string)
  description = "Existing Monitoring channels; an empty list creates console-only incidents."
  default     = []

  validation {
    condition     = alltrue([for channel in var.notification_channels : can(regex("^projects/${var.project_id}/notificationChannels/[0-9]+$", channel))])
    error_message = "Use existing notification channel IDs in the service's project."
  }
}
