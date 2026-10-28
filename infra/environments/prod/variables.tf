variable "project_id" {
  type        = string
  description = "Project containing the existing HistoricGuide bucket."

  validation {
    condition     = var.project_id == "basicrahgapp"
    error_message = "This import must use the existing basicrahgapp project."
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
