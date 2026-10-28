import copy
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.check_infra_plan import check_plan


class InfrastructurePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = {
            "complete": True,
            "errored": False,
            "resource_changes": [{
                "address": "module.storage.google_storage_bucket.app_data",
                "mode": "managed",
                "type": "google_storage_bucket",
                "change": {
                    "actions": ["no-op"],
                    "after": {"name": "historic-guide"},
                    "importing": {"id": "historic-guide"},
                },
            }, {
                "address": "module.secrets.google_secret_manager_secret.app_secrets",
                "mode": "managed",
                "type": "google_secret_manager_secret",
                "change": {
                    "actions": ["create"],
                    "after": {
                        "secret_id": "historicguide-secrets",
                        "project": "basicrahgapp",
                        "replication": [{"auto": [{}], "user_managed": []}],
                    },
                },
            }],
        }

    def test_bucket_import_and_empty_secret_creation_are_allowed(self) -> None:
        check_plan(self.plan)

    def test_already_imported_no_op_is_allowed(self) -> None:
        del self.plan["resource_changes"][0]["change"]["importing"]
        check_plan(self.plan)

    def test_both_resources_already_managed_are_allowed(self) -> None:
        del self.plan["resource_changes"][0]["change"]["importing"]
        self.plan["resource_changes"][1]["change"]["actions"] = ["no-op"]
        check_plan(self.plan)

    def test_mutations_are_rejected(self) -> None:
        for actions in (["create"], ["update"], ["delete"], ["delete", "create"], ["read"]):
            with self.subTest(actions=actions):
                self.plan["resource_changes"][0]["change"]["actions"] = actions
                with self.assertRaises(ValueError):
                    check_plan(self.plan)

    def test_missing_extra_or_unrelated_resources_are_rejected(self) -> None:
        for changes in (
            [], self.plan["resource_changes"][:1], self.plan["resource_changes"] * 2,
            [self.plan["resource_changes"][0]] * 2,
            [self.plan["resource_changes"][0], {
                **self.plan["resource_changes"][1], "address": "module.cloudrun.service",
            }],
        ):
            with self.subTest(changes=changes):
                plan = {**self.plan, "resource_changes": changes}
                with self.assertRaises(ValueError):
                    check_plan(plan)

    def test_wrong_bucket_or_import_id_is_rejected(self) -> None:
        for key in ("after", "importing"):
            with self.subTest(key=key):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][0]["change"][key] = {
                    "name" if key == "after" else "id": "another-bucket",
                }
                with self.assertRaises(ValueError):
                    check_plan(plan)

    def test_incomplete_errored_deferred_or_moved_plans_are_rejected(self) -> None:
        for fields in (
            {"complete": False}, {"complete": None}, {"errored": True},
            {"deferred_changes": [{"reason": "unknown"}]},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                check_plan({**self.plan, **fields})
        self.plan["resource_changes"][0]["previous_address"] = "old.bucket"
        with self.assertRaises(ValueError):
            check_plan(self.plan)

    def test_secret_updates_deletion_replacement_and_import_are_rejected(self) -> None:
        for actions in (["update"], ["delete"], ["delete", "create"], ["read"]):
            with self.subTest(actions=actions):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][1]["change"]["actions"] = actions
                with self.assertRaises(ValueError):
                    check_plan(plan)
        self.plan["resource_changes"][1]["change"]["importing"] = {"id": "historicguide-secrets"}
        with self.assertRaises(ValueError):
            check_plan(self.plan)

    def test_wrong_secret_identity_or_replication_is_rejected(self) -> None:
        for fields in (
            {"secret_id": "other-app"},
            {"project": "other-project"},
            {"replication": []},
            {"replication": [{"auto": [], "user_managed": [{}]}]},
            {"replication": [{"auto": [{}], "user_managed": [{}]}]},
        ):
            with self.subTest(fields=fields):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][1]["change"]["after"].update(fields)
                with self.assertRaises(ValueError):
                    check_plan(plan)

    def test_secret_versions_iam_and_regional_resources_are_rejected(self) -> None:
        for resource_type in (
            "google_secret_manager_secret_version",
            "google_secret_manager_secret_iam_member",
            "google_secret_manager_regional_secret",
        ):
            with self.subTest(resource_type=resource_type):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][1]["type"] = resource_type
                with self.assertRaises(ValueError):
                    check_plan(plan)

    def test_data_sources_and_deposed_resources_are_rejected(self) -> None:
        for fields in ({"mode": "data"}, {"deposed": "old-instance"}):
            with self.subTest(fields=fields):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][1].update(fields)
                with self.assertRaises(ValueError):
                    check_plan(plan)

    def test_cli_rejects_invalid_plan_with_explicit_error_and_nonzero_exit(self) -> None:
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / "check_infra_plan.py")],
            input="{}", text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn("::error::", result.stderr)


if __name__ == "__main__":
    unittest.main()
