# Fork GHCR AMD64 Build Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, test, and publish the fork's `local-customizations` branch as a public `linux/amd64` image at `ghcr.io/geekxtop/subconverter-extended` while keeping local machines build-free.

**Architecture:** A fork-only workflow builds a SHA-scoped candidate with the repository's pinned dependency snapshot, runs the existing Docker smoke suite against its digest, checks that the branch head is still current, and only then promotes the digest to deployable tags. A static unittest guards the fork-specific branch, registry, architecture, permissions, promotion order, and Compose image without modifying the upstream build workflow.

**Tech Stack:** GitHub Actions, Docker Buildx, GHCR, Python unittest, Docker Compose, existing dependency snapshot and smoke-test scripts.

## Global Constraints

- Build only `linux/amd64`; do not add ARM runners, QEMU, or multi-platform output.
- Trigger automatic builds only from `local-customizations`; retain manual `workflow_dispatch` support.
- Publish only to `ghcr.io/geekxtop/subconverter-extended`; do not log in to Docker Hub or publish `aethersailor/*` images.
- Use `GITHUB_TOKEN` with only `contents: read` and `packages: write` workflow permissions.
- Build a candidate first, run smoke tests against its digest, verify the current branch SHA, then promote it to `latest`, `local-customizations`, and `sha-<12-char-sha>`.
- Leave `.github/workflows/build-dockerhub.yml` and the upstream-only `master` branch unchanged.

---

### Task 1: Add the fork workflow policy regression test

**Files:**
- Create: `tests/test_fork_ghcr_workflow.py`
- Test: `tests/test_fork_ghcr_workflow.py`

**Interfaces:**
- Consumes: expected workflow path `.github/workflows/build-fork-ghcr.yml` and `docker-compose.yml`.
- Produces: unittest discovery coverage for the fork CI contract.

- [ ] **Step 1: Write the failing test**

Create `tests/test_fork_ghcr_workflow.py`:

```python
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ForkGhcrWorkflowTests(unittest.TestCase):
    def test_workflow_is_fork_only_amd64_ghcr(self):
        workflow = (ROOT / ".github/workflows/build-fork-ghcr.yml").read_text()

        self.assertIn("- local-customizations", workflow)
        self.assertIn("packages: write", workflow)
        self.assertIn("linux/amd64", workflow)
        self.assertIn('image="ghcr.io/${GITHUB_REPOSITORY,,}"', workflow)
        self.assertNotIn("linux/arm", workflow)
        self.assertNotIn("aethersailor/subconverter-extended", workflow.lower())
        self.assertNotIn("DOCKERHUB_", workflow)

    def test_candidate_is_tested_before_deployable_tags_are_promoted(self):
        workflow = (ROOT / ".github/workflows/build-fork-ghcr.yml").read_text()

        build = workflow.index("Build candidate image")
        smoke = workflow.index("Smoke test candidate image")
        current = workflow.index("Verify current branch head")
        promote = workflow.index("Promote tested image")
        self.assertLess(build, smoke)
        self.assertLess(smoke, current)
        self.assertLess(current, promote)

    def test_compose_uses_published_fork_image(self):
        compose = (ROOT / "docker-compose.yml").read_text()

        self.assertIn(
            'image: "ghcr.io/geekxtop/subconverter-extended:latest"',
            compose,
        )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
python3 -m unittest -v tests/test_fork_ghcr_workflow.py
```

Expected: errors because `.github/workflows/build-fork-ghcr.yml` does not exist, plus the Compose assertion fails against the local-only image name.

### Task 2: Implement the fork-only GHCR workflow

**Files:**
- Create: `.github/workflows/build-fork-ghcr.yml`
- Modify: `docker-compose.yml:6`
- Test: `tests/test_fork_ghcr_workflow.py`

**Interfaces:**
- Consumes: `scripts/ci/dependency_snapshot.py`, `scripts/ci/docker-build-args.sh`, `Dockerfile`, and `.github/actions/smoke-docker-image`.
- Produces: tested `linux/amd64` GHCR tags and a Compose deployment reference.

- [ ] **Step 1: Add the minimal workflow**

Create `.github/workflows/build-fork-ghcr.yml` with these stages in one `ubuntu-latest` job:

1. Checkout and Python unittest discovery.
2. Validate and export the committed dependency snapshot.
3. Derive lower-case GHCR image name, SHA tag, version, and commit build date.
4. Login only to GHCR using `${{ github.token }}`.
5. Build and push a `linux/amd64` candidate with `docker/build-push-action@v6`, existing build arguments, and registry cache.
6. Run `.github/actions/smoke-docker-image` against the candidate digest.
7. Query the GitHub API and fail if `local-customizations` no longer points at `${{ github.sha }}`.
8. Promote the digest with `docker buildx imagetools create` to `latest`, `local-customizations`, and the SHA tag.
9. Inspect the raw OCI index and require exactly one runnable `linux/amd64` platform while allowing Buildx provenance attestation descriptors.

- [ ] **Step 2: Point Compose at the published image**

Change:

```yaml
image: "subconverter-extended:latest"
```

to:

```yaml
image: "ghcr.io/geekxtop/subconverter-extended:latest"
```

- [ ] **Step 3: Run the focused test and verify GREEN**

Run:

```bash
python3 -m unittest -v tests/test_fork_ghcr_workflow.py
```

Expected: all three tests pass.

### Task 3: Verify and publish the workflow change

**Files:**
- Modify: none beyond Tasks 1-2.

**Interfaces:**
- Consumes: committed workflow and tests.
- Produces: `origin/local-customizations` containing the CI implementation and a triggered GitHub Actions run.

- [ ] **Step 1: Run all local guards**

Run:

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/check_sync_guards.py
git diff --check
```

Expected: all unittest cases pass, sync guards pass, and no whitespace errors are reported.

- [ ] **Step 2: Commit the implementation**

Run:

```bash
git add .github/workflows/build-fork-ghcr.yml docker-compose.yml tests/test_fork_ghcr_workflow.py docs/superpowers/plans/2026-08-06-fork-ghcr-amd64-plan.md
git commit -m "ci(local): publish amd64 fork image to GHCR"
```

- [ ] **Step 3: Push only the local customization branch**

Run:

```bash
git push origin local-customizations:local-customizations
```

Expected: the push triggers `Build Fork GHCR AMD64` on the new commit; no push is sent to upstream.

### Task 4: Verify the first GitHub build and package

**Files:**
- Modify only if the live workflow exposes an implementation defect.

**Interfaces:**
- Consumes: the GitHub Actions run and GHCR package created by Task 3.
- Produces: a public, deployable, single-platform image.

- [ ] **Step 1: Monitor the run to completion**

Run:

```bash
gh run list -R GeekXtop/SubConverter-Extended --workflow build-fork-ghcr.yml --limit 1
gh run watch -R GeekXtop/SubConverter-Extended <run-id> --exit-status
```

Expected: checkout, Python tests, Docker/C++ build, smoke tests, head verification, promotion, and manifest verification all succeed.

- [ ] **Step 2: Make the new GHCR package public**

After the first package exists, update `users/GeekXtop/packages/container/subconverter-extended` to `visibility=public` using the authenticated GitHub API.

- [ ] **Step 3: Verify the published manifest and repository refs**

Run:

```bash
docker buildx imagetools inspect ghcr.io/geekxtop/subconverter-extended:latest
git fetch --all --prune
git status --short --branch
git ls-remote --heads origin master local-customizations
```

Expected: `latest` reports one runnable `linux/amd64` image (plus optional Buildx attestation descriptors), the local branch matches `origin/local-customizations`, `master` remains the upstream-only commit, and the worktree is clean.
