# SubConverter-Extended Branch Sync and Default Remote Policy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the fork into an upstream-only master and a local-customizations branch, then carry the local no-default-remote policy across the current upstream code.

**Architecture:** Preserve the existing working-tree patch as a committed local branch, fast-forward master to upstream/master, and rebase the local branch onto that clean mirror. The policy layer stays intentionally small: example configs are opt-out/empty, settings loaders never synthesize a remote URL, and the active TOML ruleset import contains no Aethersailor-owned remote entries.

**Tech Stack:** Git remotes/branches, C++ settings loader, INI/TOML/YAML example configuration, Python 3 policy test, CMake build.

## Global Constraints

- master must contain only upstream history and track upstream/master.
- local-customizations must retain the six pre-existing local file changes and track the fork remote as origin/local-customizations.
- Never push to upstream; all pushes use an explicit origin refspec.
- An empty default_external_config means no implicit external template.
- Only active default configuration is changed; explicit user-supplied URLs and compatibility URL parsing remain available.

---

### Task 1: Capture the existing fork patch and create the branch split

**Files:**
- Modify: Git refs and working-tree state only.

**Interfaces:**
- Produces: local-customizations containing the current six-file patch as a recoverable commit.
- Produces: master ready to fast-forward to upstream/master.

- [ ] **Step 1: Record the exact starting state**

Run:

~~~bash
git status --short --branch
git diff --name-status
git diff -- base/pref.example.ini base/pref.example.toml base/pref.example.yml docker-compose.yml src/handler/interfaces.cpp src/handler/settings.cpp
git rev-parse master upstream/master
~~~

Expected: six modified paths, no staged changes, and master still at a178233898e6145310e7704009da1949304125af.

- [ ] **Step 2: Create the local customization branch without discarding changes**

Run:

~~~bash
git switch -c local-customizations master
git add base/pref.example.ini base/pref.example.toml base/pref.example.yml docker-compose.yml src/handler/interfaces.cpp src/handler/settings.cpp
git commit -m "chore(local): isolate fork customizations"
~~~

Expected: the six local edits are committed on local-customizations; git status --short is empty.

- [ ] **Step 3: Fast-forward the sync branch to the fetched upstream tip**

Run:

~~~bash
git switch master
git merge --ff-only upstream/master
git status --short --branch
~~~

Expected: master points at 88e41ea44356579200d605b82d986aaad6ebd900, has no local changes, and no merge commit is created.

- [ ] **Step 4: Rebase the customization commit onto the clean sync branch**

Run:

~~~bash
git rebase master local-customizations
~~~

If Git stops in the known overlapping files, resolve each file by keeping the upstream structure and reapplying only these local behaviors: empty default_external_config, no synthesized fallback URL, local image name subconverter-extended:latest, and MANAGED_CONFIG_PREFIX set to http://localhost:25500. Continue with:

~~~bash
git add base/pref.example.ini base/pref.example.toml base/pref.example.yml docker-compose.yml src/handler/interfaces.cpp src/handler/settings.cpp
git rebase --continue
~~~

Expected: local-customizations is a descendant of master with one local customization commit and no unresolved index.

- [ ] **Step 5: Publish both branch roles to the fork remote**

Run:

~~~bash
git push origin master:master
git push -u origin local-customizations:local-customizations
~~~

Expected: origin/master equals upstream/master; origin/local-customizations points to the rebased local branch; upstream is not contacted for push.

### Task 2: Add a regression test for default remote policy (RED first)

**Files:**
- Create: tests/test_default_remote_policy.py

**Interfaces:**
- Produces: a Python test executable with pytest that enforces the no-implicit-COCR policy.

- [ ] **Step 1: Write the failing policy test on the rebased branch**

Create tests/test_default_remote_policy.py with:

~~~python
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


def test_example_configs_disable_implicit_external_config():
    ini = (ROOT / "base/pref.example.ini").read_text()
    toml = (ROOT / "base/pref.example.toml").read_text()
    yaml = (ROOT / "base/pref.example.yml").read_text()

    assert re.search(r"(?m)^default_external_config\s*=\s*$", ini)
    assert re.search(r'(?m)^default_external_config\s*=\s*""\s*$', toml)
    assert re.search(r'(?m)^\s*default_external_config:\s*""\s*$', yaml)


def test_settings_loader_has_no_implicit_cocr_url():
    settings = (ROOT / "src/handler/settings.cpp").read_text()

    assert "Custom_OpenClash_Rules@refs/heads/main/cfg/Custom_Clash.ini" not in settings
    assert "if (global.defaultExtConfig.empty())" not in settings


def test_active_toml_rulesets_have_no_cocr_remote_entries():
    rulesets = (ROOT / "base/snippets/rulesets.toml").read_text().splitlines()

    active_lines = [
        line for line in rulesets
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert not any("Custom_OpenClash_Rules" in line for line in active_lines)
    assert not any(
        "testingcf.jsdelivr.net/gh/Aethersailor" in line
        for line in active_lines
    )
~~~

- [ ] **Step 2: Run the new test and confirm it catches the incoming defaults**

Run:

~~~bash
python3 -m pytest -q tests/test_default_remote_policy.py
~~~

Expected: at least test_active_toml_rulesets_have_no_cocr_remote_entries fails against the rebased upstream code because base/snippets/rulesets.toml contains active testingcf.jsdelivr.net/gh/Aethersailor/Custom_OpenClash_Rules entries.

### Task 3: Apply the no-default-remote policy (GREEN)

**Files:**
- Modify: base/pref.example.ini
- Modify: base/pref.example.toml
- Modify: base/pref.example.yml
- Modify: base/snippets/rulesets.toml
- Modify: src/handler/settings.cpp

**Interfaces:**
- Consumes: the failing policy test from Task 2.
- Produces: explicit opt-in behavior for all default external/COCR remote sources.

- [ ] **Step 1: Clear the three example defaults and correct their comments**

Set the three default_external_config values to the format-specific empty value already used by the fork (empty, "", "") and state in both Chinese and English that empty means no fallback template.

- [ ] **Step 2: Remove synthesized defaults from all settings readers**

In the YAML, TOML, and INI reader paths in src/handler/settings.cpp, retain the default_external_config read but remove each global.defaultExtConfig empty-value assignment. Leave fallback_to_default_external_config parsing and the explicit candidate logic intact.

- [ ] **Step 3: Remove active COCR URLs from the imported TOML ruleset list**

Delete the active ruleset entries whose URL contains Custom_OpenClash_Rules or testingcf.jsdelivr.net/gh/Aethersailor; retain the surrounding built-in GEOSITE/GEOIP/FINAL entries and valid type/interval pairs. Update the file header so it no longer claims the list mirrors a remote COCR configuration.

- [ ] **Step 4: Run the policy test and verify GREEN**

Run:

~~~bash
python3 -m pytest -q tests/test_default_remote_policy.py
~~~

Expected: all tests pass.

- [ ] **Step 5: Commit the policy change**

Run:

~~~bash
git add tests/test_default_remote_policy.py base/pref.example.ini base/pref.example.toml base/pref.example.yml base/snippets/rulesets.toml src/handler/settings.cpp
git commit -m "fix(local): disable implicit remote defaults"
~~~

### Task 4: Build, run focused compatibility checks, and verify branch invariants

**Files:**
- Modify: none beyond commits from Tasks 1–3.

- [ ] **Step 1: Configure and build the rebased customization branch**

Run:

~~~bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
~~~

Expected: CMake configuration and the subconverter target complete successfully.

- [ ] **Step 2: Run the focused policy and available compatibility tests**

Run:

~~~bash
python3 -m pytest -q tests/test_default_remote_policy.py
python3 -m pytest -q tests/test_sync_upstream_parser.py 2>/dev/null || true
~~~

Expected: the policy test passes; if the optional upstream-sync parser test is absent, record that it was not available rather than treating the absence as a product failure.

- [ ] **Step 3: Verify refs and worktrees without mutating them**

Run:

~~~bash
git status --short --branch
git branch -vv
git rev-parse master upstream/master
git merge-base --is-ancestor master local-customizations
git diff --check master..local-customizations
git log --graph --decorate --oneline --all -n 12
~~~

Expected: master equals upstream/master, local-customizations is its descendant, the working tree is clean, and git diff --check emits no whitespace errors.

- [ ] **Step 4: Push the final customization tip**

Run:

~~~bash
git push origin local-customizations:local-customizations
~~~

Expected: the fork remote contains the tested local branch tip and no push is sent to upstream.
