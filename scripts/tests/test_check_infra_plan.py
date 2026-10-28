import copy
from pathlib import Path
import subprocess
import sys
import unittest

from scripts.check_infra_plan import check_plan


class InfrastructurePlanTests(unittest.TestCase):
    def setUp(self) -> None:
        self.image = "europe-southwest1-docker.pkg.dev/basicrahgapp/historicguide-repo/historicguide@sha256:" + "a" * 64
        self.plan = {
            "complete": True,
            "errored": False,
            "variables": {"app_container_image": {"value": self.image}},
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
                        "secret_id": "historicguide-secrets", "project": "basicrahgapp",
                        "replication": [{"auto": [{}], "user_managed": []}],
                    },
                },
            }, {
                "address": "module.artifact_registry.google_artifact_registry_repository.default",
                "mode": "managed",
                "type": "google_artifact_registry_repository",
                "change": {
                    "actions": ["update"],
                    "importing": {
                        "id": "projects/basicrahgapp/locations/europe-southwest1/repositories/historicguide-repo",
                    },
                    "after": {
                        "project": "basicrahgapp", "location": "europe-southwest1",
                        "repository_id": "historicguide-repo", "format": "DOCKER",
                        "mode": "STANDARD_REPOSITORY",
                        "cleanup_policy_dry_run": False,
                        "cleanup_policies": [{
                            "id": "keep-last-2-historicguide", "action": "KEEP",
                            "most_recent_versions": [{
                                "keep_count": 2, "package_name_prefixes": ["historicguide"],
                            }],
                        }, {
                            "id": "delete-old-historicguide", "action": "DELETE",
                            "condition": [{"tag_state": "ANY", "package_name_prefixes": ["historicguide"]}],
                        }],
                    },
                },
            }],
        }
        registry = self.plan["resource_changes"][2]["change"]
        registry["before"] = copy.deepcopy(registry["after"])
        registry["before"]["cleanup_policies"] = []
        registry["before"]["cleanup_policy_dry_run"] = True
        self.plan["resource_changes"].extend([{
            "address": "module.cloudrun.google_cloud_run_v2_service.backend",
            "mode": "managed", "type": "google_cloud_run_v2_service",
            "change": {
                "actions": ["create"],
                "after": {
                    "project": "basicrahgapp", "location": "europe-southwest1",
                    "name": "historicguide-backend", "ingress": "INGRESS_TRAFFIC_ALL",
                    "deletion_protection": False,
                    "traffic": [{"type": "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST", "percent": 100}],
                    "template": [{
                        "service_account": "historicguide@basicrahgapp.iam.gserviceaccount.com",
                        "scaling": [{"min_instance_count": 1, "max_instance_count": 1}],
                        "vpc_access": [{
                            "egress": "PRIVATE_RANGES_ONLY",
                            "network_interfaces": [{
                                "subnetwork": "projects/basicrahgapp/regions/europe-southwest1/subnetworks/serverless-egress-subnet",
                            }],
                        }],
                        "containers": [{
                            "image": self.image,
                            "ports": [{"container_port": 8080}],
                            "resources": [{"limits": {"cpu": "2", "memory": "2Gi"}}],
                            "startup_probe": [{"http_get": [{
                                "path": "/api/health", "port": 8080, "http_headers": [],
                            }]}],
                            "env": [
                                {"name": name, "value": value} for name, value in {
                                    "ENV": "GCP", "QDRANT_HOST": "10.0.1.2", "QDRANT_PORT": "6333",
                                    "GOOGLE_CLOUD_PROJECT": "basicrahgapp",
                                    "GOOGLE_CLOUD_LOCATION": "europe-southwest1",
                                }.items()
                            ] + [{
                                "name": "APP_SECRETS_JSON",
                                "value_source": [{"secret_key_ref": [{
                                    "secret": "historicguide-secrets", "version": "latest",
                                }]}],
                            }],
                        }],
                    }],
                },
            },
        }, {
            "address": "module.cloudrun.google_cloud_run_service_iam_member.public_access",
            "mode": "managed", "type": "google_cloud_run_service_iam_member",
            "change": {
                "actions": ["create"],
                "after": {
                    "project": "basicrahgapp", "location": "europe-southwest1",
                    "service": "historicguide-backend",
                    "role": "roles/run.invoker", "member": "allUsers",
                },
            },
        }])

    def test_import_and_metadata_creation_are_allowed(self) -> None:
        check_plan(self.plan)

    def test_already_imported_no_op_is_allowed(self) -> None:
        del self.plan["resource_changes"][0]["change"]["importing"]
        check_plan(self.plan)

    def test_all_resources_already_managed_are_allowed(self) -> None:
        del self.plan["resource_changes"][0]["change"]["importing"]
        for resource in self.plan["resource_changes"]:
            resource["change"].pop("importing", None)
            resource["change"]["actions"] = ["no-op"]
        check_plan(self.plan)

    def test_bucket_mutations_are_rejected(self) -> None:
        for actions in (["create"], ["update"], ["delete"], ["delete", "create"], ["read"]):
            with self.subTest(actions=actions):
                self.plan["resource_changes"][0]["change"]["actions"] = actions
                with self.assertRaises(ValueError):
                    check_plan(self.plan)

    def test_missing_extra_duplicate_or_unrelated_resources_are_rejected(self) -> None:
        for changes in (
            [], self.plan["resource_changes"][:2], self.plan["resource_changes"] * 2,
            [self.plan["resource_changes"][0]] * 3,
            [*self.plan["resource_changes"][:2], {
                **self.plan["resource_changes"][2], "address": "module.cloudrun.service",
            }],
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                check_plan({**self.plan, "resource_changes": changes})

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

    def test_secret_and_registry_mutations_and_imports_are_rejected(self) -> None:
        for index in (1, 2):
            for actions in (["update"], ["delete"], ["delete", "create"], ["read"]):
                with self.subTest(index=index, actions=actions):
                    plan = copy.deepcopy(self.plan)
                    plan["resource_changes"][index]["change"].pop("importing", None)
                    plan["resource_changes"][index]["change"]["actions"] = actions
                    with self.assertRaises(ValueError):
                        check_plan(plan)
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"][index]["change"]["importing"] = {"id": "existing"}
            with self.assertRaises(ValueError):
                check_plan(plan)

    def test_wrong_secret_identity_or_replication_is_rejected(self) -> None:
        for fields in (
            {"secret_id": "other-app"}, {"project": "other-project"},
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
            "google_secret_manager_secret_version", "google_secret_manager_secret_iam_member",
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

    def test_wrong_registry_identity_or_dry_run_is_rejected(self) -> None:
        for fields in (
            {"project": "other-project"}, {"location": "us-central1"},
            {"repository_id": "portfolio-repo"}, {"format": "NPM"},
            {"mode": "REMOTE_REPOSITORY"},
            {"cleanup_policy_dry_run": True},
        ):
            with self.subTest(fields=fields):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][2]["change"]["after"].update(fields)
                with self.assertRaises(ValueError):
                    check_plan(plan)

    def test_registry_import_cannot_change_other_metadata_or_create_repository(self) -> None:
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][2]["change"]["after"]["description"] = "Unrelated change"
        with self.assertRaises(ValueError):
            check_plan(plan)
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][2]["change"]["actions"] = ["create"]
        with self.assertRaises(ValueError):
            check_plan(plan)

    def test_retention_must_be_two_total_in_the_application_package(self) -> None:
        for fields in ({"keep_count": 3}, {"package_name_prefixes": ["other-app"]}):
            with self.subTest(fields=fields):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][2]["change"]["after"]["cleanup_policies"][0]["most_recent_versions"][0].update(fields)
                with self.assertRaises(ValueError):
                    check_plan(plan)
        for policies in ([], self.plan["resource_changes"][2]["change"]["after"]["cleanup_policies"][:1]):
            plan = copy.deepcopy(self.plan)
            plan["resource_changes"][2]["change"]["after"]["cleanup_policies"] = policies
            with self.assertRaises(ValueError):
                check_plan(plan)

    def test_cleanup_delete_scope_cannot_be_broadened(self) -> None:
        for fields in (
            {"package_name_prefixes": []}, {"tag_state": "TAGGED"},
            {"older_than": "86400s"}, {"tag_prefixes": ["old"]},
        ):
            with self.subTest(fields=fields):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][2]["change"]["after"]["cleanup_policies"][1]["condition"][0].update(fields)
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

    def test_cloud_run_in_place_image_update_is_allowed(self) -> None:
        self.plan["resource_changes"][3]["change"]["actions"] = ["update"]
        check_plan(self.plan)

    def test_cloud_run_wrong_identity_and_destructive_actions_are_rejected(self) -> None:
        for fields in (
            {"project": "other-project"}, {"name": "basicragapp-backend"},
            {"location": "us-central1"}, {"ingress": "INGRESS_TRAFFIC_INTERNAL_ONLY"},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][3]["change"]["after"].update(fields)
                check_plan(plan)
        for actions in (["delete"], ["delete", "create"], ["read"]):
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][3]["change"]["actions"] = actions
                check_plan(plan)

    def test_image_must_be_digest_pinned_in_our_package_and_match_plan_input(self) -> None:
        for image in (
            self.image.split("@")[0] + ":latest", self.image.replace("historicguide-repo", "portfolio-repo"),
            self.image[:-1], self.image.replace("sha256:", "sha256:Z"),
        ):
            with self.subTest(image=image), self.assertRaises(ValueError):
                plan = copy.deepcopy(self.plan)
                plan["variables"]["app_container_image"]["value"] = image
                plan["resource_changes"][3]["change"]["after"]["template"][0]["containers"][0]["image"] = image
                check_plan(plan)
        self.plan["resource_changes"][3]["change"]["after"]["template"][0]["containers"][0]["image"] = self.image[:-1] + "b"
        with self.assertRaises(ValueError):
            check_plan(self.plan)

    def test_wrong_runtime_identity_scaling_and_network_are_rejected(self) -> None:
        for fields in (
            {"service_account": "other@basicrahgapp.iam.gserviceaccount.com"},
            {"scaling": [{"min_instance_count": 0, "max_instance_count": 10}]},
            {"vpc_access": [{"egress": "ALL_TRAFFIC", "network_interfaces": []}]},
            {"vpc_access": [{"egress": "PRIVATE_RANGES_ONLY", "network_interfaces": [{"subnetwork": "qdrant-subnet"}]}]},
            {"volumes": [{"name": "unexpected"}]},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][3]["change"]["after"]["template"][0].update(fields)
                check_plan(plan)

    def test_wrong_secret_plaintext_payload_and_extra_env_are_rejected(self) -> None:
        for replacement in (
            {"name": "APP_SECRETS_JSON", "value": "never-in-terraform"},
            {"name": "APP_SECRETS_JSON", "value_source": [{"secret_key_ref": [{"secret": "other-app", "version": "latest"}]}]},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ValueError):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][3]["change"]["after"]["template"][0]["containers"][0]["env"][-1] = replacement
                check_plan(plan)
        plan = copy.deepcopy(self.plan)
        plan["resource_changes"][3]["change"]["after"]["template"][0]["containers"][0]["env"].append(
            {"name": "GEMINI_API_KEY", "value": "never-in-terraform"},
        )
        with self.assertRaises(ValueError):
            check_plan(plan)

    def test_wrong_container_resources_port_probe_and_entrypoint_are_rejected(self) -> None:
        for fields in (
            {"ports": [{"container_port": 9000}]},
            {"resources": [{"limits": {"cpu": "8", "memory": "8Gi"}}]},
            {"startup_probe": [{"http_get": [{"path": "/", "port": 8080, "http_headers": []}]}]},
            {"command": ["custom-command"]},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][3]["change"]["after"]["template"][0]["containers"][0].update(fields)
                check_plan(plan)

    def test_public_invoker_cannot_target_another_service_role_or_member(self) -> None:
        for fields in (
            {"service": "portfolio"}, {"project": "other-project"},
            {"service": "v1/projects/other-project/locations/europe-southwest1/services/historicguide-backend"},
            {"service": "v1/projects/basicrahgapp/locations/us-central1/services/historicguide-backend"},
            {"service": "v1/projects/basicrahgapp/locations/europe-southwest1/services/portfolio"},
            {"service": "v1/projects/basicrahgapp/locations/europe-southwest1/services/historicguide-backend-extra"},
            {"role": "roles/run.admin"}, {"member": "allAuthenticatedUsers"},
        ):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                plan = copy.deepcopy(self.plan)
                plan["resource_changes"][4]["change"]["after"].update(fields)
                check_plan(plan)

    def test_refreshed_public_invoker_full_service_path_allows_image_update(self) -> None:
        public = self.plan["resource_changes"][4]["change"]
        public["actions"] = ["no-op"]
        public["after"]["service"] = (
            "v1/projects/basicrahgapp/locations/europe-southwest1/services/historicguide-backend"
        )
        self.plan["resource_changes"][3]["change"]["actions"] = ["update"]
        check_plan(self.plan)

    def test_refreshed_public_invoker_does_not_allow_iam_mutations(self) -> None:
        public = self.plan["resource_changes"][4]["change"]
        public["after"]["service"] = (
            "v1/projects/basicrahgapp/locations/europe-southwest1/services/historicguide-backend"
        )
        for actions in (["update"], ["delete"], ["delete", "create"]):
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                public["actions"] = actions
                check_plan(self.plan)


if __name__ == "__main__":
    unittest.main()
