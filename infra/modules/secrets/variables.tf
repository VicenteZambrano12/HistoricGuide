variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "cloud_run_service_account_email" {
  type        = string
  description = "Runtime service account that must be able to read the app secrets."
}

variable "common_labels" {
  type = map(string)
}
