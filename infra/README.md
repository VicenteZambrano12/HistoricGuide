# HistoricGuide Terraform migration

Earlier stages adopted `gs://historic-guide` and created the global
`historicguide-secrets` container in `basicrahgapp`. Its JSON versions were
populated separately through the CLI; Terraform manages only secret metadata.

The current stage preserves the bucket, secret, and dedicated Docker repository
and creates **`historicguide-backend` in `europe-southwest1`** through the existing
workflow. It follows the Cloud Run example: public frontend/API, 2 CPU / 2 GiB,
and minimum/maximum one instance. The minimum instance incurs ongoing idle costs.
It retains **two images total**, not a current image plus two previous ones.
It does not upload secret versions or create Qdrant/network resources.
Only the storage, secrets, Artifact Registry, and Cloud Run modules are retained.
The unused networking example has been removed: the existing VPC, subnets,
firewall rules, and Qdrant VM remain externally managed.
Other applications' infrastructure is not changed.

The existing workflow, [terraform-deploy.yml](../.github/workflows/terraform-deploy.yml),
keeps its original sequence: merge a same-repository `dev` PR into `main`,
build/push or reuse the image, resolve its immutable digest, plan, upload the
saved plan, then apply that exact plan in the protected `prod` environment.
The earlier repository bootstrap is complete, so publication now precedes the
plan: Cloud Run must review and deploy the exact same digest. Image publication
and pruning occur before approval; service deployment occurs only after approval.
Both jobs remain in the same workflow; no separate deployment workflow is introduced.
It does not run on a push, an unmerged PR close, a differently named source branch,
or a manual Actions dispatch.

## Safety and state

- The import block adopts `historic-guide` at
  `module.storage.google_storage_bucket.app_data`.
- State uses the existing backend bucket but a **new, isolated** prefix:
  `gs://terraform_bucket_portfolio/historic_guide/prod/default.tfstate`.
  The `basic_rag_app_tfstate`, `orchestrator_app`, and `portfolio` states are
  not read or migrated. Do not copy their states into this prefix.
- Bucket name, location, storage class, public access prevention, uniform
  access, encryption enforcement, and seven-day soft deletion match the
  existing bucket.
- No new labels are added. Terraform attribution labels are disabled so that
  adoption does not require updating the bucket.
- `prevent_destroy = true` and `force_destroy = false` protect the bucket.
- The [plan checker](../scripts/check_infra_plan.py) allows exactly the bucket,
  `module.secrets.google_secret_manager_secret.app_secrets`,
  `module.artifact_registry.google_artifact_registry_repository.default`,
  `module.cloudrun.google_cloud_run_v2_service.backend`, and
  `module.cloudrun.google_cloud_run_service_iam_member.public_access`. The bucket
  must remain unchanged, with an optional import of `historic-guide`. The
  global `historicguide-secrets` secret may be created or remain unchanged;
  updates, deletion, replacement, imports of other secrets, extra resources,
  moves, incomplete plans, and deferred changes are rejected before upload and
  again before apply. The dedicated repository may be imported or unchanged;
  only its cleanup policies may change during import. Its two-image cleanup
  policies are enforced. Cloud Run may be created or updated in place only with
  the plan input's immutable HistoricGuide digest, expected account/subnet,
  JSON secret reference, runtime settings, resources, and API startup probe.
  Its only allowed IAM resource grants `roles/run.invoker` to `allUsers` on
  `historicguide-backend`, matching the public example. Deletion/replacement,
  secret versions, additional IAM, networking, and unrelated resources are rejected.
- The secret also uses `prevent_destroy = true`. Only its metadata enters
  Terraform state; there is no secret value in configuration, plans, or state.
- Bucket objects and bucket IAM are deliberately outside Terraform in this
  step. Existing runtime access and all PDFs/prompts remain unchanged.
- The backend bucket itself is pre-existing bootstrap infrastructure; this
  configuration does not import it. The expected cloud writes are state/locks,
  image uploads, removal of images beyond the newest two, and the reviewed
  Cloud Run service/public-invoker creation or in-place service updates.

## 1. One-time GCP bootstrap (manual)

The initial bucket bootstrap is already configured for this repository. The
commands below document that setup; do not recreate verified existing resources.
Secret permissions are documented in **1d**, registry permissions in **1e**,
and the approved Cloud Run bootstrap in **1f**.
Use an administrator identity authorized to create WIF providers/custom roles
and add IAM bindings. These are **not** workflow steps:
GitHub needs these permissions before Terraform can authenticate or store state.
No JSON service-account key is used by GitHub.

The specified account is reused for this migration:
`historicguide@basicrahgapp.iam.gserviceaccount.com`. These grants add state
access to its existing runtime PDF/prompt access. A separate deployment account
can be considered later, but is not introduced here.

### 1a. Add a dedicated federation provider

The existing `github-provider` excludes HistoricGuide. Leave its condition and
other repositories untouched. Create a separate provider inside the existing
`github-pool`, restricted to this repository's numeric ID, owner ID, and `main`:

```sh
gcloud iam workload-identity-pools providers create-oidc github-historicguide \
  --project=basicrahgapp \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="HistoricGuide GitHub Actions" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository_id == '1093704843' && assertion.repository_owner_id == '181724456' && assertion.ref == 'refs/heads/main'"

gcloud iam service-accounts add-iam-policy-binding \
  historicguide@basicrahgapp.iam.gserviceaccount.com \
  --project=basicrahgapp \
  --role=roles/iam.workloadIdentityUser \
  --condition=None \
  --member="principalSet://iam.googleapis.com/projects/31049783945/locations/global/workloadIdentityPools/github-pool/attribute.repository/VicenteZambrano12/HistoricGuide"
```

The merged-PR event uses the base branch `main`; the apply job's `prod`
environment changes its OIDC subject, but not its repository/ref claims.
The mapping and repository-scoped principal support both jobs.
If creating a provider reports `ALREADY_EXISTS`, describe and verify that
provider's issuer, mapping, and condition rather than overwriting it blindly.

### 1b. Read existing bucket metadata (no bucket mutation permission)

```sh
gcloud iam roles create historicGuideBucketImport \
  --project=basicrahgapp \
  --title="HistoricGuide bucket import metadata" \
  --description="Read bucket metadata for import-only Terraform plans" \
  --permissions=storage.buckets.get \
  --stage=GA

gcloud storage buckets add-iam-policy-binding gs://historic-guide \
  --member="serviceAccount:historicguide@basicrahgapp.iam.gserviceaccount.com" \
  --condition=None \
  --role="projects/basicrahgapp/roles/historicGuideBucketImport"
```

Do not grant Storage Admin, Owner, Editor, or project-wide object access.
The existing conditioned runtime `roles/storage.objectViewer` binding on
`docs/` and `prompts/` is separate and must remain intact.

### 1c. Access only the new state prefix

Terraform needs to list workspaces and create/read/update/delete its state and
lock objects. Object listing is bucket-scoped, so grant that separately from
prefix-restricted object operations:

```sh
gcloud iam roles create historicGuideStateList \
  --project=basicrahgapp \
  --title="HistoricGuide Terraform workspace listing" \
  --description="List workspace object names in the existing state bucket" \
  --permissions=storage.objects.list \
  --stage=GA

gcloud storage buckets add-iam-policy-binding gs://terraform_bucket_portfolio \
  --member="serviceAccount:historicguide@basicrahgapp.iam.gserviceaccount.com" \
  --condition=None \
  --role="projects/basicrahgapp/roles/historicGuideStateList"

gcloud storage buckets add-iam-policy-binding gs://terraform_bucket_portfolio \
  --member="serviceAccount:historicguide@basicrahgapp.iam.gserviceaccount.com" \
  --role=roles/storage.objectAdmin \
  --condition="title=historicguide-terraform-state,expression=resource.name.startsWith('projects/_/buckets/terraform_bucket_portfolio/objects/historic_guide/prod/')"
```

Listing exposes object names in the shared backend bucket, not other projects'
state contents. Reading/writing/deleting state objects is limited to the new
prefix. State access needs no project-level role or permission to mutate the
corpus bucket. If a custom role already exists, inspect its permissions before
reuse.

### 1d. Create the empty secret through Terraform, not the CLI

The Secret Manager API must already be enabled. The deployment account needs
`secretmanager.secrets.create` on the project because the new secret does not
exist yet. Metadata reads are conditioned to the single application secret.
These roles grant no payload reads, version creation, secret updates/deletion,
or IAM-policy changes:

```sh
gcloud iam roles create historicGuideSecretCreate \
  --project=basicrahgapp \
  --title="HistoricGuide empty secret creation" \
  --description="Create Secret Manager containers; no version or payload permissions" \
  --permissions=secretmanager.secrets.create \
  --stage=GA

gcloud iam roles create historicGuideSecretMetadata \
  --project=basicrahgapp \
  --title="HistoricGuide secret metadata read" \
  --description="Read Secret Manager container metadata only" \
  --permissions=secretmanager.secrets.get \
  --stage=GA

gcloud projects add-iam-policy-binding basicrahgapp \
  --member="serviceAccount:historicguide@basicrahgapp.iam.gserviceaccount.com" \
  --role="projects/basicrahgapp/roles/historicGuideSecretCreate" \
  --condition=None

gcloud projects add-iam-policy-binding basicrahgapp \
  --member="serviceAccount:historicguide@basicrahgapp.iam.gserviceaccount.com" \
  --role="projects/basicrahgapp/roles/historicGuideSecretMetadata" \
  --condition="title=historicguide-secret-metadata,expression=resource.name.endsWith('/secrets/historicguide-secrets')"
```

The create permission is necessarily project-scoped; the workflow plan checker
limits this migration to the named secret. Secret Manager Admin is unnecessary;
runtime Secret Accessor was added later, only on this secret, as described in 1f.
If a newly created custom role is temporarily
reported as missing, allow IAM propagation and retry only the failed binding.
Do not run `gcloud secrets create`: creation belongs to the reviewed Terraform
plan and apply.

The JSON payload was uploaded separately through the CLI; runtime access is
documented in 1f. Do not
put real values in Terraform variables, source files, commits, or plan artifacts.

### 1e. Repository-scoped publishing and retention permissions

The Artifact Registry API must already be enabled. Unlike Secret Manager and
Storage, Artifact Registry does not support resource-name IAM conditions for
this bootstrap. To avoid granting project-wide image access, the empty
repository was explicitly approved for one-time CLI creation. The workflow
imports it into Terraform state, configures retention, and publishes the image.
Only the empty repository and its IAM binding were created ahead of the PR;
no image was uploaded.

The following commands document that administrator bootstrap. Do not recreate
the repository if it already exists:

```sh
gcloud artifacts repositories create historicguide-repo \
  --project=basicrahgapp --location=europe-southwest1 \
  --repository-format=docker \
  --description="HistoricGuide Docker images managed by Terraform"

gcloud iam roles create historicGuideRegistryImages \
  --project=basicrahgapp \
  --title="HistoricGuide Docker publishing and retention" \
  --description="Docker publishing, cleanup metadata and old-version deletion; bound only on the application repository" \
  --permissions=artifactregistry.repositories.get,artifactregistry.repositories.update,artifactregistry.repositories.downloadArtifacts,artifactregistry.repositories.uploadArtifacts,artifactregistry.dockerimages.get,artifactregistry.dockerimages.list,artifactregistry.packages.get,artifactregistry.packages.list,artifactregistry.files.get,artifactregistry.files.list,artifactregistry.files.download,artifactregistry.files.upload,artifactregistry.tags.create,artifactregistry.tags.get,artifactregistry.tags.list,artifactregistry.tags.update,artifactregistry.tags.delete,artifactregistry.versions.get,artifactregistry.versions.list,artifactregistry.versions.delete \
  --stage=GA

gcloud artifacts repositories add-iam-policy-binding historicguide-repo \
  --project=basicrahgapp --location=europe-southwest1 \
  --member="serviceAccount:historicguide@basicrahgapp.iam.gserviceaccount.com" \
  --role="projects/basicrahgapp/roles/historicGuideRegistryImages"
```

The account can read/update repository metadata and publish/prune images only
in this repository. It cannot create/delete repositories, change IAM, or access
other repositories' images. No project-level Artifact Registry role is granted.
The import block uses
`projects/basicrahgapp/locations/europe-southwest1/repositories/historicguide-repo`.

### Image selection and two-image expiration rule

The image base is
`europe-southwest1-docker.pkg.dev/basicrahgapp/historicguide-repo/historicguide`.
New builds are tagged with the full workflow commit SHA. The workflow retains
the original application path filtering: changed application sources build a
new image unless that SHA already exists; infrastructure-only changes reuse
the newest digest. An empty repository always causes a build.

After push, the workflow resolves an immutable `@sha256:...` image reference.
The [image helper](../scripts/registry_images.py) lists only this application
package, orders versions by creation time, deletes older digests including
their tags, and verifies that the newest two remain (or one after the first
push). It fails without deleting anything if the selected digest is missing
or older than those two. Failed API calls and failed retention checks fail
the workflow rather than reporting success.

Terraform also preserves the example's native cleanup rule: `KEEP` the two
most recent `historicguide` versions and `DELETE` older versions, including
tagged ones. Native cleanup is asynchronous; the workflow's explicit prune
enforces the cap immediately after successful publication. Buildx disables
provenance/SBOM side manifests and builds only `linux/amd64` so retention counts
application images rather than extra attestation artifacts.

The digest is passed as `TF_VAR_app_container_image` when generating the saved
plan, and recorded with the Cloud Run URL in the deployment summary.
The workflow never reads the application JSON payload.

### 1f. Approved Cloud Run bootstrap and runtime configuration

These grants have already been applied through the CLI to
`historicguide@basicrahgapp.iam.gserviceaccount.com`:

| Scope | Role / permissions |
| --- | --- |
| Project `basicrahgapp` | Custom `historicGuideRunDeploy`: `run.services.create`, `run.services.get`, `run.services.update`, `run.services.getIamPolicy`, `run.services.setIamPolicy`, `run.operations.get` |
| The HistoricGuide service account itself | `roles/iam.serviceAccountUser` to attach that account to Cloud Run |
| Secret `historicguide-secrets` only | `roles/secretmanager.secretAccessor` |
| Subnet `serverless-egress-subnet` only | `roles/compute.networkUser` |

The project-level deployment role is an explicitly approved bootstrap exception:
Cloud Run does not support resource-name IAM conditions. Until it is narrowed,
this role can also update settings/IAM on other Cloud Run services in this project,
but cannot delete services. After the first successful deployment, service-management
permissions can be bound directly to `historicguide-backend`, retaining separately
scoped project operation reads. Do not attempt that before the service exists.
No Owner, Editor, Cloud Run Admin, or project-wide secret access was granted.

The existing Cloud Run service agent already has `roles/run.serviceAgent`, which
provides same-project image pulling and Direct VPC networking permissions.
No new network/subnet/firewall or service account is created. Direct VPC egress
uses the existing `serverless-egress-subnet` (`10.0.2.0/24`) in
`portfolio-demo-vpc`, with `PRIVATE_RANGES_ONLY`. The existing
`allow-cloud-run-to-qdrant` firewall rule permits TCP 6333 from that subnet to
`qdrant-vm` at `10.0.1.2`.

Cloud Run injects the global secret's `latest` version into `APP_SECRETS_JSON`,
as in the example. The backend accepts a nonempty JSON object of string values;
invalid JSON/configuration types fail container startup without exposing values.
Configuration precedence is process environment, JSON secret, root `.env`, then
defaults. Cloud Run explicitly sets `ENV=GCP`, project/location, and the private
Qdrant host/port. Other settings, including both API keys, bucket, models and
collection, come from the single JSON secret. The container uses its attached
account's Application Default Credentials, never the local service-account key.
Terraform stores only the secret reference, not its payload.
New secret versions do not refresh running instances; deploy a new revision to
consume changed values.

The first Cloud Run merge rebuilds the image because the existing published
image predates JSON-secret support. It is pushed and digest-resolved by the same
workflow before planning; no local Docker installation is necessary.

**Runtime prerequisite:** `qdrant-vm` was verified **TERMINATED** during this
preparation and has not been started. The `historic_guide` collection was absent
at the earlier check and needs rechecking when the VM is available. This step
does not start the VM or migrate its data. `/api/health` is process liveness:
successful frontend/health checks do not prove chat or Qdrant readiness.

## 2. Configure GitHub before merging

Open [repository settings](https://github.com/VicenteZambrano12/HistoricGuide/settings).

1. **Actions → General:** ensure Actions and the referenced checkout, Google,
   HashiCorp, Docker Buildx, path-filter, and artifact actions are allowed.
2. **Secrets and variables → Actions → Variables:** add these *repository*
   variables:

   | Name | Value |
   | --- | --- |
   | `GCP_PROJECT_ID` | `basicrahgapp` |
   | `GCP_REGION` | `europe-southwest1` |

3. Under **Secrets**, add these *repository* secrets (not environment-only
   secrets; the plan job also needs them):

   | Name | Value |
   | --- | --- |
   | `GCP_WORKLOAD_IDENTITY_PROVIDER` | `projects/31049783945/locations/global/workloadIdentityPools/github-pool/providers/github-historicguide` |
   | `GCP_TERRAFORM_SERVICE_ACCOUNT` | `historicguide@basicrahgapp.iam.gserviceaccount.com` |

4. **Environments → New environment:** create `prod`. Under deployment
   protection rules, enable **Required reviewers** and select yourself or an
   authorized reviewer. For a solo repository, leave **Prevent self-review**
   disabled if you will approve your own run. Under **Selected branches and
   tags**, add two **Branch** rules: `main` and `refs/pull/*/merge`. GitHub can
   evaluate a pull-request deployment against its synthetic merge ref, even
   for this merged-PR workflow. Keeping only `main` can reject the apply job
   before it starts. Keep required reviewers enabled; the workflow also
   requires a merged, same-repository `dev` PR targeting `main`.
5. Save and verify the reviewer rule **before merging**. `environment: prod`
   alone does not require approval; without the rule, apply runs automatically.
   If your GitHub plan/repository settings do not allow required reviewers,
   stop rather than merging without the intended approval gate.

No additional GitHub variables or secrets are needed for Cloud Run.
The repository and image path come from Terraform. GitHub's hosted runner
provides Docker; local Docker is not required to trigger the workflow. No
application payload or service-account JSON key is passed into the build.
Allow a few minutes for new IAM bindings to propagate.

## 3. Commit only this migration on `dev`

Review `git status` and do not use `git add .`. Stage only this migration:

```sh
git add .github/workflows/terraform-deploy.yml \
  infra/README.md \
  infra/environments/prod/main.tf \
  infra/environments/prod/outputs.tf \
  infra/environments/prod/variables.tf \
  infra/modules/cloudrun/main.tf infra/modules/cloudrun/variables.tf \
  backend/src/container.py backend/src/utils/general/GeminiApiCall.py \
  backend/tests/test_container.py backend/tests/test_gemini_client.py \
  scripts/check_infra_plan.py scripts/tests/test_check_infra_plan.py \
  README.md

git diff --cached --stat
git diff --cached --check
git commit -m "infra: deploy HistoricGuide to Cloud Run through Terraform" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push -u origin dev
```

Confirm you are on `dev` before committing. Never stage `.env`, the
service-account JSON, `.terraform/`, a plan file, or state files.
Configuration comes from the two GitHub repository variables and the
workflow-resolved application image digest; no `terraform.tfvars` file is needed.

## 4. Merge and approve through GitHub

1. Open **Pull requests → New pull request**: base `main`, compare `dev`.
2. Review **Files changed**: the active root preserves storage/secret/registry
   and activates only the adapted Cloud Run module and its public invoker.
   No networking, Qdrant, secret-version, or additional IAM resources should appear.
3. Merge the PR. This triggers the existing **closed + merged dev PR**
   workflow. Simply pushing `dev` will not run it.
4. Open **Actions → Deploy GCP Infrastructure (Terraform)** and select the run.
5. Open **Build image and plan Cloud Run → Show Terraform Plan**.
   The first Cloud Run deployment must show **2 to add, 0 to change, 0 to destroy**:
   only `historicguide-backend` and its public invoker. Bucket, secret metadata,
   and repository must stay unchanged. Check the image is in
   `historicguide-repo/historicguide@sha256:...`, port 8080, the expected account,
   private subnet, and JSON secret reference. No secret values should appear.
6. Only after inspecting that plan, click **Review deployments → prod →
   Approve and deploy**. The apply job downloads and revalidates the saved
   plan; it never calculates a different plan for apply.
7. Approve within the plan artifact's one-day retention period. If it expires,
   rerun all jobs to generate and review a fresh plan.
8. Check **Terraform Apply**, then **Verify Cloud Run frontend and API** succeed.
   The startup probe and HTTP checks use `/api/health`; `/` must serve HTML.
   No post-apply bucket verification or second drift plan is added.
9. Open **Record Cloud Run deployment** and the job summary for the URL and
   immutable image reference. Open the URL to view the frontend. Test chat only
   after Qdrant is running with the correct collection and embedding model.

The expected result is the isolated state tracking five resources, the bucket
and JSON secret versions unchanged, and the public frontend/API running from
the workflow-published digest in the dedicated repository.
The import block can stay: later runs are idempotent and do not re-import a
resource already in this state.

## Troubleshooting and local checks

- `refs/pull/<number>/merge` is not allowed to deploy: add the **Branch** rule
  `refs/pull/*/merge` to `prod` alongside `main`, leaving required reviewers
  enabled. Rerun all jobs to generate a fresh plan, then review and approve it.
  Do not disable environment protection or change the workflow trigger.
- `attribute condition` / federation denied: check the new provider path,
  repository IDs, and that this is a merged same-repository `dev` → `main` PR.
- `iam.serviceAccounts.getAccessToken` denied: check the repository-scoped
  `roles/iam.workloadIdentityUser` binding on the specified account.
- State list denied: check the unconditional custom workspace-list role.
  State read/write/lock denied: check the object-prefix condition separately.
- Bucket metadata denied: check `storage.buckets.get` on `historic-guide`;
  runtime object read permission alone cannot import bucket metadata.
- Secret creation denied: check the project-level custom create role in 1d.
  Secret refresh denied: check the conditioned metadata-read role separately.
- Registry import denied or not found: check the administrator bootstrap in
  1e and the repository-scoped custom role. Repository reads, policy updates,
  Docker pushes, and retention all use this direct binding; do not replace it
  with an unsupported project-level resource-name condition or broaden access.
- A Docker build/push failure now happens before the Cloud Run plan/apply.
  Fix the build error and rerun all jobs; already-published SHA tags are reused.
- Cloud Run secret access denied: check the direct Secret Accessor binding on
  `historicguide-secrets`, its enabled version, and the runtime account.
- Private Qdrant failures: start/check the existing VM separately, verify its
  collection/model and API key, then subnet/firewall connectivity. Do not change
  unrelated network resources or assume a healthy HTTP process means chat works.
- Unexpected changes in the plan: **do not approve** or weaken the checker.
  Compare the live resource metadata to its module and fix the mismatch.
- The public-invoker checker accepts the initial short service name and the
  provider's refreshed `v1/projects/basicrahgapp/locations/europe-southwest1/services/historicguide-backend`
  path. These identify the same service; other services, projects, regions,
  roles, members, and IAM updates remain forbidden.
- Do not use `terraform init -migrate-state`, copy example state, force-unlock
  an active run, run local apply, or use `-target` to bypass the restricted root.

With Terraform 1.13.5 available, these checks do not apply infrastructure
changes. A working directory already initialized against the GCS backend may
still require authorized Application Default Credentials during initialization:

```sh
terraform -chdir=infra/environments/prod fmt -check . ../../modules/storage ../../modules/secrets ../../modules/artifact_registry ../../modules/cloudrun
terraform -chdir=infra/environments/prod init -backend=false -input=false -lockfile=readonly
terraform -chdir=infra/environments/prod validate
ENV=LOCAL PYTHONPATH=backend uv run --project backend --locked python -m unittest scripts.tests.test_check_infra_plan scripts.tests.test_registry_images backend.tests.test_container backend.tests.test_gemini_client
```