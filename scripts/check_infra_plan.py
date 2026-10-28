"""Allow only HistoricGuide storage, secret metadata, and the dedicated image repository."""

import json
import sys


BUCKET_ADDRESS = "module.storage.google_storage_bucket.app_data"
SECRET_ADDRESS = "module.secrets.google_secret_manager_secret.app_secrets"
REGISTRY_ADDRESS = "module.artifact_registry.google_artifact_registry_repository.default"
REGISTRY_ID = "projects/basicrahgapp/locations/europe-southwest1/repositories/historicguide-repo"


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
    if len(changes) != 3 or {resource.get("address") for resource in changes} != {
        BUCKET_ADDRESS, SECRET_ADDRESS, REGISTRY_ADDRESS,
    }:
        raise ValueError("The plan must contain exactly the bucket, application secret, and image repository.")
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
        else:
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


if __name__ == "__main__":
    try:
        check_plan(json.load(sys.stdin))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("Verified: HistoricGuide bucket, secret metadata, and dedicated repository with two-image retention only.")
