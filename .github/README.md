# Organization defaults for `tensor4all`

This repository is public and does two jobs for the organization.

## 1. The pull request template is org-wide with no per-repository file

`pull_request_template.md` at the root here is a **default community health file**: GitHub applies it
to every repository in the organization that has none of its own. Precedence inside a target
repository is `.github/` → root → `docs/`, so a repository that wants different text still overrides it
by adding its own `.github/pull_request_template.md`.

Nothing needs copying. `tenferro-rs` keeps its own template and keeps it.

## 2. The check needs one small file per repository. Second correction, and why.

I have been wrong about this twice, so here is the record.

**First** I said organization-wide enforcement was impossible, because the ruleset rule list only shows
"Require status checks to pass". That was wrong: the `workflows` rule exists, and the API parses and
resolves it for this organization (`repository_id: 0` → `422 Workflow source repository not found`;
a path not on `main` → `422 … does not contain a workflow at: …`).

**Then** I said the four-line caller was unnecessary. Also wrong, for a reason that matters more than
the file count: **a workflow required by an organization ruleset is run by the ruleset runner on
`opened`, `synchronize` and `reopened` only.** No `edited`. This check exists to catch a description
with no evidence, and the two ways a description changes are exactly the two the runner ignores: fix
the description after a failure (stays red), or delete the evidence after a success (stays green). A
repository's own `pull_request` workflow does fire on `edited`, so the caller is what buys the
property, not red tape.

The caller, in `.github/workflows/pr-verification.yml` of each repository that opts in:

```yaml
name: PR verification section
on:
  pull_request:
    types: [opened, edited, reopened, synchronize]
  merge_group:
permissions:
  contents: read
  pull-requests: read
jobs:
  body:
    uses: tensor4all/.github/.github/workflows/pr-verification.yml@main
```

`merge_group` is there because a repository with a merge queue cannot satisfy a required check that
never runs for its merge group; the reusable workflow fetches the description by PR number in that case,
since the merge group event carries no `pull_request` payload.

Then one organization ruleset requiring the check `PR verification section / body` on
`~DEFAULT_BRANCH` for the repositories that have the caller. Start it in **evaluate** mode: `active`
would turn every open pull request in those repositories red at once.

## Why a check and not a convention

Across this organization we merged green pull requests whose test never ran (a shell function used as
a command, `exit 127`), whose `cargo package` verified a build and not a test run, whose changed line
could be mutated without a failure, and whose threshold contradicted the measurement quoted beside it.
A reviewer catches that while paying attention; a check catches it when they are not.

Passing conditions and the opt-out are specified in `scripts/check_pr_body.py`. Its cases live in
`scripts/test_check_pr_body.py` — one per counterexample found by an adversarial review of the first
version, which passed all eight hand-run cases and still let five wrong bodies through. `self-test.yml`
runs them and asserts that **the template itself is rejected**: a template that passes its own check is
one whose placeholder text reads as evidence.
