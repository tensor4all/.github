# Organization defaults for `tensor4all`

This repository is public and serves two jobs.

## 1. The pull request template is org-wide already

`pull_request_template.md` at the root of this repository is a **default community health file**:
GitHub uses it for every repository in the organization that does not have its own PR template.
Nothing needs to be copied into individual repositories, and a repository that wants different text
still overrides it by adding its own `.github/pull_request_template.md`.

Precedence in a target repository: `.github/` → repository root → `docs/`.

## 2. Enforcement needs one small file per repository

GitHub rulesets can require a status check, and "Require workflows to pass" (a workflow living in
another repository) no longer exists in the ruleset rules. So the check has to run **in** each
repository, calling the reusable workflow here:

```yaml
# .github/workflows/pr-verification.yml in the target repository
name: PR verification section
on: [pull_request]
jobs:
  body:
    uses: tensor4all/.github/.github/workflows/pr-verification.yml@main
```

Then create (or extend) an organization ruleset requiring the check `PR verification section / body`
on the default branch of the repositories that opted in. Repositories without the caller are left out
of that ruleset: a required check that never runs would block every pull request forever.

## Why a check and not a convention

Across this organization we merged green pull requests whose test never ran (a shell function used as
a command, `exit 127`), whose `cargo package` verified a build and not a test run, whose changed line
could be mutated without a failure, and whose threshold contradicted the measurement quoted beside it.
A reviewer can catch that when they are paying attention; a check catches it when they are not.

Passing conditions, and the opt-out, are in `scripts/check_pr_body.py` (the docstring is the spec).
