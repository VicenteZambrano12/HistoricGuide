import copy
import unittest

from scripts.check_bucket_plan import check_plan


class BucketPlanTests(unittest.TestCase):
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
            }],
        }

    def test_import_only_is_allowed(self) -> None:
        check_plan(self.plan)

    def test_already_imported_no_op_is_allowed(self) -> None:
        del self.plan["resource_changes"][0]["change"]["importing"]
        check_plan(self.plan)

    def test_mutations_are_rejected(self) -> None:
        for actions in (["create"], ["update"], ["delete"], ["delete", "create"], ["read"]):
            with self.subTest(actions=actions):
                self.plan["resource_changes"][0]["change"]["actions"] = actions
                with self.assertRaises(ValueError):
                    check_plan(self.plan)

    def test_missing_extra_or_unrelated_resources_are_rejected(self) -> None:
        for changes in ([], self.plan["resource_changes"] * 2, [{
            **self.plan["resource_changes"][0], "address": "module.cloudrun.service",
        }]):
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


if __name__ == "__main__":
    unittest.main()
