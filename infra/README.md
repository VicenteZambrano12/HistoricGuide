# HistoricGuide Terraform migration

The first stage adopted the existing `gs://historic-guide` bucket in
`basicrahgapp`, region `europe-southwest1`. The current stage keeps that bucket
unchanged and creates **one empty global Secret Manager secret**,
`historicguide-secrets`, with automatic replication.

The secret is reserved for a future single JSON object containing application
configuration. This stage creates **no secret version, JSON payload, or runtime
accessor IAM binding**. It does not read `.env`, copy objects, deploy the
application, create Qdrant resources, or activate the other example modules.
The existing example secrets for other applications are not imported or changed.

The existing workflow, [terraform-deploy.yml](../.github/workflows/terraform-deploy.yml),
keeps its original sequence: merge a same-repository `dev` PR into `main`,
plan, upload the saved plan, then apply that exact plan in the `prod` environment.
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
- The [plan checker](../scripts/check_infra_plan.py) allows exactly the bucket
  and `module.secrets.google_secret_manager_secret.app_secrets`. The bucket
  must remain unchanged, with an optional import of `historic-guide`. The
  global `historicguide-secrets` secret may be created or remain unchanged;
  updates, deletion, replacement, imports of other secrets, extra resources,
  moves, incomplete plans, and deferred changes are rejected before upload and
  again before apply. Secret-version and IAM resources are not allowed.
- The secret also uses `prevent_destroy = true`. Only its metadata enters
  Terraform state; there is no secret value in configuration, plans, or state.
- Bucket objects and bucket IAM are deliberately outside Terraform in this
  step. Existing runtime access and all PDFs/prompts remain unchanged.
- The backend bucket itself is pre-existing bootstrap infrastructure; this
  configuration does not import it. The expected cloud writes are state/locks
  and creation of the empty application secret.

## 1. One-time GCP bootstrap (manual)

The initial bucket bootstrap is already configured for this repository. The
commands below document that setup; do not recreate verified existing resources.
For the secrets stage, the additional permissions are documented in **1d**.
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
limits this migration to the named secret. Do not grant Secret Manager Admin
or Secret Accessor for this step. If a newly created custom role is temporarily
reported as missing, allow IAM propagation and retry only the failed binding.
Do not run `gcloud secrets create`: creation belongs to the reviewed Terraform
plan and apply.

Later, upload one JSON payload as a secret version through an explicitly
authorized secret-value workflow and wire runtime access separately. Do not
put real values in Terraform variables, source files, commits, or plan artifacts.

## 2. Configure GitHub before merging

Open [repository settings](https://github.com/VicenteZambrano12/HistoricGuide/settings).

1. **Actions → General:** ensure Actions and the referenced checkout, Google,
   HashiCorp, and artifact actions are allowed.
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

No additional GitHub variables or secrets are needed for the empty-secret
stage. No Artifact Registry, Docker, Neon, application payload, or
service-account JSON key secret is required. Allow a few minutes for new GCP
IAM bindings to propagate before running the workflow.

## 3. Commit only this migration on `dev`

There are other uncommitted application changes. Do not use `git add .`.
Review the listed paths, then stage only:

```sh
git add .github/workflows/terraform-deploy.yml \
  infra/README.md \
  infra/environments/prod/main.tf \
  infra/environments/prod/outputs.tf \
  infra/modules/secrets/main.tf \
  infra/modules/secrets/variables.tf \
  infra/modules/secrets/outputs.tf \
  scripts/check_infra_plan.py scripts/tests/test_check_infra_plan.py
git add -u -- scripts/check_bucket_plan.py scripts/tests/test_check_bucket_plan.py

git diff --cached --stat
git diff --cached --check
git commit -m "infra: create empty global HistoricGuide secret" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
git push -u origin dev
```

Confirm you are on `dev` before committing. Never stage `.env`, the
service-account JSON, `.terraform/`, a plan file, or state files. The empty
example `terraform.tfvars` is not needed; configuration comes from the two
GitHub repository variables.

## 4. Merge and approve through GitHub

1. Open **Pull requests → New pull request**: base `main`, compare `dev`.
2. Review **Files changed**: the active root must contain only the storage
   module, its retained import block, and the empty secret module. No active
   Cloud Run, networking, registry, Qdrant, secret-version, or IAM resources
   should appear.
3. Merge the PR. This triggers the existing **closed + merged dev PR**
   workflow. Simply pushing `dev` will not run it.
4. Open **Actions → Deploy GCP Infrastructure (Terraform)** and select the run.
5. Open **Plan bucket and empty application secret → Show Terraform Plan**.
   With the bucket already adopted, this stage must say **1 to add, 0 to
   change, 0 to destroy**, creating only
   `module.secrets.google_secret_manager_secret.app_secrets`. If the bucket
   has not yet been adopted, **1 to import** is also allowed. New metadata
   outputs are expected. If both resources are already managed, a zero-change
   plan is valid.
6. Only after inspecting that plan, click **Review deployments → prod →
   Approve and deploy**. The apply job downloads and revalidates the saved
   plan; it never calculates a different plan for apply.
7. Approve within the plan artifact's one-day retention period. If it expires,
   rerun all jobs to generate and review a fresh plan.
8. Check **Terraform Apply** succeeds and reports the secret creation. The
   workflow ends after applying the saved plan; it does not run a post-apply
   bucket verification or a second drift plan.

The expected result is the existing state tracking both resources, the existing
bucket at the same URL with the same contents/IAM, and an empty global secret
named `historicguide-secrets` with **zero versions**. There is no application
deployment and no runtime secret access configured yet.
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
- Unexpected changes in the plan: **do not approve** or weaken the checker.
  Compare the live resource metadata to its module and fix the mismatch.
- Do not use `terraform init -migrate-state`, copy example state, force-unlock
  an active run, run local apply, or use `-target` to bypass the restricted root.

With Terraform 1.13.5 available, these checks do not access remote state:

```sh
terraform -chdir=infra/environments/prod fmt -check . ../../modules/storage ../../modules/secrets
terraform -chdir=infra/environments/prod init -backend=false -input=false -lockfile=readonly
terraform -chdir=infra/environments/prod validate
uv run --project backend --locked python -m unittest scripts.tests.test_check_infra_plan
```