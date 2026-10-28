"""Allow only the existing bucket and an empty global application secret."""

import json
import sys


BUCKET_ADDRESS = "module.storage.google_storage_bucket.app_data"
SECRET_ADDRESS = "module.secrets.google_secret_manager_secret.app_secrets"


def check_plan(plan: dict) -> None:
    if plan.get("errored") or plan.get("complete") is not True:
        raise ValueError("The infrastructure plan must be complete and error-free.")
    if plan.get("deferred_changes"):
        raise ValueError("Deferred resource changes are not allowed.")
    changes = plan.get("resource_changes", [])
    if len(changes) != 2 or {resource.get("address") for resource in changes} != {
        BUCKET_ADDRESS, SECRET_ADDRESS,
    }:
        raise ValueError("The plan must contain exactly the existing bucket and application secret.")
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
        else:
            if (
                resource.get("type") != "google_secret_manager_secret"
                or change.get("actions") not in (["create"], ["no-op"])
                or change.get("importing") is not None
            ):
                raise ValueError("Only empty secret creation or an unchanged secret is allowed.")
            if after.get("secret_id") != "historicguide-secrets" or after.get("project") != "basicrahgapp":
                raise ValueError("Unexpected application secret ID or project.")
            replication = after.get("replication") or []
            if (
                len(replication) != 1 or len(replication[0].get("auto") or []) != 1
                or replication[0].get("user_managed")
            ):
                raise ValueError("The global secret must use automatic replication.")


if __name__ == "__main__":
    try:
        check_plan(json.load(sys.stdin))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("Verified: unchanged historic-guide bucket and empty global historicguide-secrets secret only.")
