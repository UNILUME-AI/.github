# .github — org defaults

Org-wide defaults for `UNILUME-AI`. This is the **双门禁 enforcement hub**: it ships the
machine gate (reusable CI) and the human gate (policy-bot policy), plus shared community-health
files that every repo inherits unless it overrides them.

## Contents

| Path | Role |
|---|---|
| `.github/workflows/reusable-ts-machine-gate.yml` | 机器门 · reusable CI (`workflow_call`): prettier + eslint + tsc + test, all from `@unilume/conventions` |
| `policy.yml` | 人评门 · Palantir policy-bot org-default approval policy |
| `PULL_REQUEST_TEMPLATE.md` · `ISSUE_TEMPLATE/` | Org-default PR / issue templates aligned to the planning ladder |
| `profile/README.md` | Org profile page |

## Wire the machine gate in a TS repo

```yaml
# .github/workflows/ci.yml in the business repo
name: ci
on:
  pull_request:
    types: [opened, synchronize, reopened]
  push: { branches: [main] }
jobs:
  gate:
    uses: UNILUME-AI/.github/.github/workflows/reusable-ts-machine-gate.yml@main
    with:
      node-version: '22'
```

Mark the `gate / machine-gate` context **required** in branch protection.

## Wire the human gate

Two layers, escalating:

1. **Interim (works today):** branch protection "require ≥1 approval" + a per-repo `CODEOWNERS`.
   CODEOWNERS is **not** inheritable from this repo — each repo needs its own.
2. **Full (Palantir policy-bot):** deploy the policy-bot GitHub App, set its policy path to fall
   back to this repo's `policy.yml`, and mark the `policy-bot` status check required.

Rationale: constitution §VII — enforcement lives in git/CI, not in any single agent.
See `UNILUME-AI/scrum:governance/` for the constitution and tiered-SDD R-tiers.
