locals {
  service_filter = join("\n", [
    "resource.type=\"cloud_run_revision\"",
    "resource.labels.project_id=\"${var.project_id}\"",
    "resource.labels.service_name=\"${var.service_name}\"",
    "resource.labels.location=\"${var.region}\"",
  ])
  error_filter = "${local.service_filter}\n(severity>=ERROR OR jsonPayload.level=\"ERROR\" OR jsonPayload.status_code>=500 OR httpRequest.status>=500)"
}

resource "google_logging_project_bucket_config" "application" {
  project        = var.project_id
  location       = var.region
  bucket_id      = var.bucket_id
  retention_days = var.retention_days
  description    = "${var.environment}: ${var.service_name} structured application and frontend/API access logs."

  lifecycle {
    prevent_destroy = true
  }
}

resource "google_logging_project_sink" "application" {
  project     = var.project_id
  name        = "${var.bucket_id}-sink"
  destination = "logging.googleapis.com/projects/${var.project_id}/locations/${var.region}/buckets/${var.bucket_id}"
  filter      = local.service_filter
  description = "${var.environment}: route only ${var.service_name} logs to its private log bucket."
  # Same-project log buckets need no destination grant; true also matches provider refresh.
  unique_writer_identity = true
  disabled               = false

  depends_on = [google_logging_project_bucket_config.application]
}

resource "google_logging_project_exclusion" "default_duplicate" {
  project     = var.project_id
  name        = "${var.bucket_id}-default-copy"
  description = "${var.environment}: avoid duplicate new service logs in _Default after dedicated routing exists."
  filter      = local.service_filter
  disabled    = false

  depends_on = [google_logging_project_sink.application]
}

resource "google_logging_metric" "errors" {
  project     = var.project_id
  name        = "${var.bucket_id}-errors"
  description = "${var.environment}: ERROR or HTTP 5xx log entries, not deduplicated requests."
  filter      = local.error_filter
  disabled    = false

  metric_descriptor {
    metric_kind  = "DELTA"
    value_type   = "INT64"
    unit         = "1"
    display_name = "${var.environment}: ${var.service_name} error entries"
  }
}

resource "google_monitoring_alert_policy" "errors" {
  project               = var.project_id
  display_name          = "${var.environment}: ${var.service_name} error entries"
  combiner              = "OR"
  enabled               = true
  notification_channels = var.notification_channels
  user_labels = {
    env         = var.environment
    application = "historicguide"
  }

  conditions {
    display_name = "At least ${var.error_threshold_count} error entries in five minutes"
    condition_threshold {
      filter          = "resource.type=\"cloud_run_revision\" AND metric.type=\"logging.googleapis.com/user/${google_logging_metric.errors.name}\""
      comparison      = "COMPARISON_GT"
      threshold_value = var.error_threshold_count - 1
      duration        = "0s"
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_DELTA"
        cross_series_reducer = "REDUCE_SUM"
      }
      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "Inspect the dedicated ${var.bucket_id} bucket for ERROR/5xx entries from ${var.service_name}. Counts are log entries; a single failed request may produce multiple entries. Empty notification_channels means console incidents only."
    mime_type = "text/markdown"
  }
}
