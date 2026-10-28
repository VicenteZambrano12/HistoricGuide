"""Reject any Terraform plan beyond adopting the existing HistoricGuide bucket."""

import json
import sys


ADDRESS = "module.storage.google_storage_bucket.app_data"


def check_plan(plan: dict) -> None:
    if plan.get("errored") or plan.get("complete") is not True:
        raise ValueError("The bucket plan must be complete and error-free.")
    if plan.get("deferred_changes"):
        raise ValueError("Deferred resource changes are not allowed.")
    changes = plan.get("resource_changes", [])
    if len(changes) != 1:
        raise ValueError("The plan must contain exactly the existing bucket.")
    resource = changes[0]
    if (
        resource.get("address") != ADDRESS
        or resource.get("mode") != "managed"
        or resource.get("type") != "google_storage_bucket"
        or resource.get("previous_address")
    ):
        raise ValueError("Unexpected resource or resource move in the bucket-only plan.")
    change = resource["change"]
    if change.get("actions") != ["no-op"]:
        raise ValueError("Bucket creation, updates, deletion, and replacement are forbidden.")
    if change.get("after", {}).get("name") != "historic-guide":
        raise ValueError("The planned bucket must be historic-guide.")
    importing = change.get("importing")
    if importing is not None and importing.get("id") != "historic-guide":
        raise ValueError("Unexpected bucket import ID.")


if __name__ == "__main__":
    try:
        check_plan(json.load(sys.stdin))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1) from error
    print("Verified: existing historic-guide bucket only; no infrastructure changes.")
