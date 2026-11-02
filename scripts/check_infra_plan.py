"""Restrict the migration plan to HistoricGuide metadata and its Cloud Run service."""

import json
import re
import sys


BUCKET_ADDRESS = "module.storage.google_storage_bucket.app_data"
SECRET_ADDRESS = "module.secrets.google_secret_manager_secret.app_secrets"
REGISTRY_ADDRESS = "module.artifact_registry.google_artifact_registry_repository.default"
REGISTRY_ID = "projects/basicrahgapp/locations/europe-southwest1/repositories/historicguide-repo"
CLOUDRUN_ADDRESS = "module.cloudrun.google_cloud_run_v2_service.backend"
PUBLIC_ADDRESS = "module.cloudrun.google_cloud_run_service_iam_member.public_access"
PUBLIC_SERVICE_NAMES = {
    "historicguide-backend",
    "v1/projects/basicrahgapp/locations/europe-southwest1/services/historicguide-backend",
}
IMAGE_PATTERN = r"europe-southwest1-docker\.pkg\.dev/basicrahgapp/historicguide-repo/historicguide@sha256:[0-9a-f]{64}"
LOGGING_RESOURCES = {
    "module.logging.google_logging_project_bucket_config.application": "google_logging_project_bucket_config",
    "module.logging.google_logging_project_sink.application": "google_logging_project_sink",
    "module.logging.google_logging_project_exclusion.default_duplicate": "google_logging_project_exclusion",
    "module.logging.google_logging_metric.errors": "google_logging_metric",
    "module.logging.google_monitoring_alert_policy.errors": "google_monitoring_alert_policy",
}
SERVICE_LOG_FILTER = "\n".join([
    'resource.type="cloud_run_revision"',
    'resource.labels.project_id="basicrahgapp"',
    'resource.labels.service_name="historicguide-backend"',
    'resource.labels.location="europe-southwest1"',
])
ERROR_LOG_FILTER = SERVICE_LOG_FILTER + '\n(severity>=ERROR OR jsonPayload.level="ERROR" OR jsonPayload.status_code>=500 OR httpRequest.status>=500)'


def logging_settings(plan: dict) -> dict:
    variables = plan.get("variables", {})
    settings = {key: variables.get(key, {}).get("value") for key in (
        "environment", "log_bucket_id", "log_retention_days",
        "log_error_threshold_count", "log_notification_channels",
    )}
    bucket = settings["log_bucket_id"]
    threshold = settings["log_error_threshold_count"]
    channels = settings["log_notification_channels"]
    if (
        settings["environment"] != "prod"
        or not isinstance(bucket, str) or re.fullmatch(r"historicguide-prod-[a-z0-9-]+", bucket) is None
        or settings["log_retention_days"] not in (14, 30)
        or type(threshold) is not int or not 1 <= threshold <= 1000
        or not isinstance(channels, list)
        or any(not isinstance(channel, str) or re.fullmatch(
            r"projects/basicrahgapp/notificationChannels/[0-9]+", channel,
        ) is None for channel in channels)
    ):
        raise ValueError("Invalid production logging inputs, retention, threshold, or notification channels.")
    return settings


def check_logging(resource: dict, settings: dict) -> None:
    resource_type = LOGGING_RESOURCES[resource["address"]]
    change = resource["change"]
    after = change.get("after") or {}
    if (
        resource.get("type") != resource_type
        or change.get("actions") not in (["create"], ["update"], ["no-op"])
        or change.get("importing") is not None
        or after.get("project") != "basicrahgapp"
    ):
        raise ValueError("Only the expected logging resource creations or in-place updates are allowed.")
    bucket = settings["log_bucket_id"]
    labels = {"env": "prod", "application": "historicguide"}
    if resource_type == "google_logging_project_bucket_config":
        if (
            after.get("bucket_id") != bucket or after.get("location") != "europe-southwest1"
            or after.get("retention_days") != settings["log_retention_days"]
        ):
            raise ValueError("The log bucket must use its approved identity, region, and retention.")
    elif resource_type in ("google_logging_project_sink", "google_logging_project_exclusion"):
        expected_filter = " ".join(SERVICE_LOG_FILTER.split())
        if not isinstance(after.get("filter"), str) or " ".join(after["filter"].split()) != expected_filter:
            raise ValueError("Log routing/exclusion must match only the HistoricGuide Cloud Run service.")
        if after.get("disabled") is not False:
            raise ValueError("The dedicated log route and duplicate exclusion must remain enabled.")
        if resource_type == "google_logging_project_sink":
            if (
                after.get("name") != f"{bucket}-sink"
                or after.get("destination") != f"logging.googleapis.com/projects/basicrahgapp/locations/europe-southwest1/buckets/{bucket}"
                or after.get("unique_writer_identity") is not True
                or after.get("exclusions") or after.get("custom_writer_identity")
            ):
                raise ValueError("Route all service logs only to the same-project dedicated log bucket.")
        elif after.get("name") != f"{bucket}-default-copy":
            raise ValueError("Only the named service-specific _Default exclusion is allowed.")
    elif resource_type == "google_logging_metric":
        descriptors = after.get("metric_descriptor") or []
        if (
            after.get("name") != f"{bucket}-errors" or after.get("disabled") is not False
            or after.get("filter") != ERROR_LOG_FILTER
            or after.get("label_extractors") or after.get("value_extractor") or after.get("bucket_name")
            or len(descriptors) != 1
            or any(descriptors[0].get(key) != value for key, value in {
                "metric_kind": "DELTA", "value_type": "INT64", "unit": "1",
            }.items())
            or descriptors[0].get("labels")
        ):
            raise ValueError("Only the bounded service-only ERROR/5xx counter is allowed.")
    else:
        conditions = after.get("conditions") or []
        strategies = after.get("alert_strategy") or []
        if (
            after.get("display_name") != "prod: historicguide-backend error entries"
            or after.get("enabled") is not True or after.get("combiner") != "OR"
            or after.get("user_labels") != labels
            or after.get("notification_channels") != settings["log_notification_channels"]
            or len(conditions) != 1
            or len(strategies) != 1 or strategies[0].get("auto_close") != "1800s"
            or strategies[0].get("notification_rate_limit") or strategies[0].get("notification_channel_strategy")
        ):
            raise ValueError("Unexpected error alert identity, labels, channels, or strategy.")
        thresholds = conditions[0].get("condition_threshold") or []
        if len(thresholds) != 1:
            raise ValueError("Only one error-count threshold condition is allowed.")
        threshold = thresholds[0]
        if any(threshold.get(key) != value for key, value in {
            "filter": f'resource.type="cloud_run_revision" AND metric.type="logging.googleapis.com/user/{bucket}-errors"',
            "comparison": "COMPARISON_GT", "threshold_value": settings["log_error_threshold_count"] - 1,
            "duration": "0s",
        }.items()):
            raise ValueError("Alert must trigger at the approved five-minute error-entry threshold.")
        triggers = threshold.get("trigger") or []
        if (
            len(triggers) != 1 or triggers[0].get("count") != 1 or triggers[0].get("percent")
            or threshold.get("denominator_filter") or threshold.get("denominator_aggregations")
            or threshold.get("forecast_options")
        ):
            raise ValueError("Only a simple error-count threshold trigger is allowed.")
        aggregations = threshold.get("aggregations") or []
        if len(aggregations) != 1 or any(aggregations[0].get(key) != value for key, value in {
            "alignment_period": "300s", "per_series_aligner": "ALIGN_DELTA",
            "cross_series_reducer": "REDUCE_SUM",
        }.items()) or aggregations[0].get("group_by_fields"):
            raise ValueError("Alert must sum five-minute error entries across all service revisions.")


def check_cloudrun(after: dict, image: str) -> None:
    expected = {
        "project": "basicrahgapp", "location": "europe-southwest1",
        "name": "historicguide-backend", "ingress": "INGRESS_TRAFFIC_ALL",
        "deletion_protection": False,
        "labels": {"env": "prod", "application": "historicguide"},
    }
    if any(after.get(key) != value for key, value in expected.items()):
        raise ValueError("Unexpected Cloud Run identity or ingress settings.")
    templates = after.get("template") or []
    if len(templates) != 1:
        raise ValueError("Exactly one Cloud Run template is required.")
    template = templates[0]
    if template.get("service_account") != "historicguide@basicrahgapp.iam.gserviceaccount.com":
        raise ValueError("Cloud Run must use the HistoricGuide service account.")
    scaling = template.get("scaling") or []
    if len(scaling) != 1 or any(scaling[0].get(key) != 1 for key in ("min_instance_count", "max_instance_count")):
        raise ValueError("Cloud Run must retain the example's single-instance scaling.")
    access = template.get("vpc_access") or []
    subnet = "projects/basicrahgapp/regions/europe-southwest1/subnetworks/serverless-egress-subnet"
    if (
        len(access) != 1 or access[0].get("egress") != "PRIVATE_RANGES_ONLY"
        or len(access[0].get("network_interfaces") or []) != 1
        or access[0]["network_interfaces"][0].get("subnetwork") != subnet
    ):
        raise ValueError("Cloud Run must reuse the existing private Qdrant subnet.")
    containers = template.get("containers") or []
    if len(containers) != 1 or containers[0].get("image") != image:
        raise ValueError("Cloud Run must deploy exactly the workflow's immutable image.")
    container = containers[0]
    if container.get("command") or container.get("args") or template.get("volumes") or container.get("volume_mounts"):
        raise ValueError("Container entrypoint overrides and secret volumes are not allowed.")
    resources = container.get("resources") or []
    ports = container.get("ports") or []
    if (
        len(resources) != 1 or resources[0].get("limits") != {"cpu": "2", "memory": "2Gi"}
        or len(ports) != 1 or ports[0].get("container_port") != 8080
    ):
        raise ValueError("Cloud Run must use port 8080 and the example's 2 CPU / 2 GiB limits.")
    env = container.get("env") or []
    by_name = {item["name"]: item for item in env}
    expected_env = {
        "ENV": "GCP", "QDRANT_HOST": "10.0.1.2", "QDRANT_PORT": "6333",
        "GOOGLE_CLOUD_PROJECT": "basicrahgapp", "GOOGLE_CLOUD_LOCATION": "europe-southwest1",
    }
    if len(env) != 6 or set(by_name) != {*expected_env, "APP_SECRETS_JSON"}:
        raise ValueError("Only the expected runtime settings and JSON secret reference are allowed.")
    if any(by_name[key].get("value") != value or by_name[key].get("value_source") for key, value in expected_env.items()):
        raise ValueError("Unexpected Cloud Run runtime configuration.")
    secret = by_name["APP_SECRETS_JSON"]
    sources = secret.get("value_source") or []
    if (
        secret.get("value") not in (None, "") or len(sources) != 1
        or sources[0].get("secret_key_ref") != [{"secret": "historicguide-secrets", "version": "latest"}]
    ):
        raise ValueError("Inject only a reference to the global JSON secret, never its payload.")
    probes = container.get("startup_probe") or []
    if len(probes) != 1 or probes[0].get("http_get") != [{"path": "/api/health", "port": 8080, "http_headers": []}]:
        raise ValueError("Cloud Run must check API startup on /api/health.")
    traffic = after.get("traffic") or []
    if len(traffic) != 1 or traffic[0].get("type") != "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST" or traffic[0].get("percent") != 100:
        raise ValueError("Cloud Run must send all traffic to the new ready revision.")


def check_registry(after: dict) -> None:
    expected = {
        "project": "basicrahgapp", "location": "europe-southwest1",
        "repository_id": "historicguide-repo", "format": "DOCKER", "mode": "STANDARD_REPOSITORY",
        "cleanup_policy_dry_run": False,
    }
    if any(after.get(key) != value for key, value in expected.items()):
        raise ValueError("Unexpected Artifact Registry identity, format, or cleanup mode.")
    policies = after.get("cleanup_policies") or []
    by_id = {policy["id"]: policy for policy in policies}
    if len(policies) != 2 or set(by_id) != {"keep-last-2-historicguide", "delete-old-historicguide"}:
        raise ValueError("The repository must have exactly the two application cleanup policies.")
    keep = by_id["keep-last-2-historicguide"]
    recent = keep.get("most_recent_versions") or []
    delete = by_id["delete-old-historicguide"]
    condition = delete.get("condition") or []
    if (
        keep.get("action") != "KEEP" or len(recent) != 1
        or recent[0].get("keep_count") != 2
        or recent[0].get("package_name_prefixes") != ["historicguide"]
        or keep.get("condition")
        or delete.get("action") != "DELETE" or len(condition) != 1
        or condition[0].get("tag_state") != "ANY"
        or condition[0].get("package_name_prefixes") != ["historicguide"]
        or any(condition[0].get(key) for key in (
            "older_than", "newer_than", "tag_prefixes", "version_name_prefixes",
        ))
        or delete.get("most_recent_versions")
    ):
        raise ValueError("Cleanup must keep two newest HistoricGuide images and delete older ones.")


def check_plan(plan: dict) -> None:
    if plan.get("errored") or plan.get("complete") is not True:
        raise ValueError("The infrastructure plan must be complete and error-free.")
    if plan.get("deferred_changes"):
        raise ValueError("Deferred resource changes are not allowed.")
    changes = plan.get("resource_changes", [])
    expected_addresses = {
        BUCKET_ADDRESS, SECRET_ADDRESS, REGISTRY_ADDRESS, CLOUDRUN_ADDRESS, PUBLIC_ADDRESS,
        *LOGGING_RESOURCES,
    }
    if len(changes) != len(expected_addresses) or {resource.get("address") for resource in changes} != expected_addresses:
        raise ValueError("The plan must contain only the five application resources and five dedicated observability resources.")
    settings = logging_settings(plan)
    image = plan.get("variables", {}).get("app_container_image", {}).get("value")
    if not isinstance(image, str) or re.fullmatch(IMAGE_PATTERN, image) is None:
        raise ValueError("The plan requires the workflow's immutable HistoricGuide image digest.")
    for resource in changes:
        if resource.get("mode") != "managed" or resource.get("previous_address") or resource.get("deposed"):
            raise ValueError("Resource reads, moves, and deposed resources are not allowed.")
        change = resource["change"]
        after = change.get("after") or {}
        if resource["address"] in LOGGING_RESOURCES:
            check_logging(resource, settings)
        elif resource["address"] == BUCKET_ADDRESS:
            if resource.get("type") != "google_storage_bucket" or change.get("actions") != ["no-op"]:
                raise ValueError("Bucket creation, updates, deletion, and replacement are forbidden.")
            if after.get("name") != "historic-guide":
                raise ValueError("The planned bucket must be historic-guide.")
            importing = change.get("importing")
            if importing is not None and importing.get("id") != "historic-guide":
                raise ValueError("Unexpected bucket import ID.")
        elif resource["address"] == SECRET_ADDRESS:
            if (
                resource.get("type") != "google_secret_manager_secret"
                or change.get("actions") not in (["create"], ["no-op"])
                or change.get("importing") is not None
            ):
                raise ValueError("Only secret metadata creation or an unchanged secret is allowed.")
            if after.get("secret_id") != "historicguide-secrets" or after.get("project") != "basicrahgapp":
                raise ValueError("Unexpected application secret ID or project.")
            replication = after.get("replication") or []
            if (
                len(replication) != 1 or len(replication[0].get("auto") or []) != 1
                or replication[0].get("user_managed")
            ):
                raise ValueError("The global secret must use automatic replication.")
        elif resource["address"] == REGISTRY_ADDRESS:
            importing = change.get("importing")
            if (
                resource.get("type") != "google_artifact_registry_repository"
                or change.get("actions") not in (["update"], ["no-op"])
                or importing is not None and importing.get("id") != REGISTRY_ID
            ):
                raise ValueError("Only the dedicated repository import or an unchanged repository is allowed.")
            check_registry(after)
            if change.get("actions") == ["update"]:
                if importing is None:
                    raise ValueError("Repository updates are only allowed while importing its cleanup policies.")
                before = change.get("before") or {}
                changed = {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
                if not changed.issubset({"cleanup_policies", "cleanup_policy_dry_run", "update_time"}):
                    raise ValueError("Repository import may change only the two-image cleanup policy.")
        elif resource["address"] == CLOUDRUN_ADDRESS:
            if (
                resource.get("type") != "google_cloud_run_v2_service"
                or change.get("actions") not in (["create"], ["update"], ["no-op"])
                or change.get("importing") is not None
            ):
                raise ValueError("Only HistoricGuide Cloud Run creation or in-place updates are allowed.")
            check_cloudrun(after, image)
        else:
            if (
                resource.get("type") != "google_cloud_run_service_iam_member"
                or change.get("actions") not in (["create"], ["no-op"])
                or change.get("importing") is not None
                or after.get("service") not in PUBLIC_SERVICE_NAMES
                or any(after.get(key) != value for key, value in {
                    "project": "basicrahgapp", "location": "europe-southwest1",
                    "role": "roles/run.invoker", "member": "allUsers",
                }.items())
            ):
                raise ValueError("Only the example's public invoker on historicguide-backend is allowed.")


if __name__ == "__main__":
    try:
        check_plan(json.load(sys.stdin))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("Verified: HistoricGuide metadata, digest-pinned Cloud Run, private log retention/routing and service-only error alerting.")
