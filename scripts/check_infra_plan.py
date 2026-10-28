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
IMAGE_PATTERN = r"europe-southwest1-docker\.pkg\.dev/basicrahgapp/historicguide-repo/historicguide@sha256:[0-9a-f]{64}"


def check_cloudrun(after: dict, image: str) -> None:
    expected = {
        "project": "basicrahgapp", "location": "europe-southwest1",
        "name": "historicguide-backend", "ingress": "INGRESS_TRAFFIC_ALL",
        "deletion_protection": False,
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
    if len(changes) != 5 or {resource.get("address") for resource in changes} != {
        BUCKET_ADDRESS, SECRET_ADDRESS, REGISTRY_ADDRESS, CLOUDRUN_ADDRESS, PUBLIC_ADDRESS,
    }:
        raise ValueError("The plan must contain only the bucket, secret, repository, Cloud Run service and public invoker.")
    image = plan.get("variables", {}).get("app_container_image", {}).get("value")
    if not isinstance(image, str) or re.fullmatch(IMAGE_PATTERN, image) is None:
        raise ValueError("The plan requires the workflow's immutable HistoricGuide image digest.")
    for resource in changes:
        if resource.get("mode") != "managed" or resource.get("previous_address") or resource.get("deposed"):
            raise ValueError("Resource reads, moves, and deposed resources are not allowed.")
        change = resource["change"]
        after = change.get("after") or {}
        if resource["address"] == BUCKET_ADDRESS:
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
                or any(after.get(key) != value for key, value in {
                    "project": "basicrahgapp", "location": "europe-southwest1",
                    "service": "historicguide-backend", "role": "roles/run.invoker", "member": "allUsers",
                }.items())
            ):
                raise ValueError("Only the example's public invoker on historicguide-backend is allowed.")


if __name__ == "__main__":
    try:
        check_plan(json.load(sys.stdin))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("Verified: HistoricGuide metadata, two-image retention, and digest-pinned Cloud Run with its public invoker only.")
