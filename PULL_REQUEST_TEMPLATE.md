<!-- Org-default PR template. A Story = one PR (constitution §III). Repos may override
     with their own .github/PULL_REQUEST_TEMPLATE.md. -->

## What & why

<!-- One paragraph. Link the parent Feature/Bug SDD and Epic. -->

- Feature / Bug: <!-- specs/NNN/ link, or scrum Epic # -->
- Epic: <!-- scrum/docs/epics/NNNN.md or Epic issue # -->

## Gate checklist (双门禁)

- [ ] **机器门**: lint / format / typecheck / tests green (reusable-ts-machine-gate or repo CI)
- [ ] **人评门**: review requested from CODEOWNERS / per policy-bot
- [ ] SDD honored: change traces to an approved spec (constitution §I)
- [ ] System-shape change writes back to central knowledge (`scrum/docs/{architecture,data,contracts}`) if applicable (§V, §VI)
- [ ] Cross-repo contract (`@unilume/sdk`) change → semver bump + contract-test (AD-14)

## Risk tier

<!-- R1 / R2 / R3 per scrum tiered-SDD; note machine-tier (F/M/S) and reviewer-familiarity. -->
