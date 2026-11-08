# Organization defaults for `tensor4all`

This repository is public and does two jobs for the organization.

## 1. The pull request template is org-wide with no per-repository file

`pull_request_template.md` at the root here is a **default community health file**: GitHub applies it
to every repository in the organization that has none of its own. Precedence inside a target
repository is `.github/` → root → `docs/`, so a repository that wants different text still overrides it
by adding its own `.github/pull_request_template.md`.

Nothing needs copying. `tenferro-rs` keeps its own template and keeps it.

## 2. The check is org-wide too, through an organization ruleset

**Correction to an earlier version of this file:** I wrote that organization-wide enforcement was
impossible because the ruleset rule list only offers "Require status checks to pass". That was wrong.
The `workflows` rule exists ("Require workflows to pass before merging") and the API accepts it for this
organization:

```
POST orgs/tensor4all/rulesets
  { "rules": [{ "type": "workflows", "parameters": { "workflows": [
      { "repository_id": 802971965,
        "path": ".github/workflows/pr-verification.yml",
        "ref": "refs/heads/main" } ] } } ] }

repository_id: 0          -> 422 "Workflow source repository not found"
path that does not exist  -> 422 "tensor4all/.github does not contain a workflow at: …"
```

Both rejections show the rule being parsed and resolved; it fails only because the file is not on
`main` yet. So the deployment is: merge this, then create one organization ruleset naming that
workflow. **No file in any target repository.** An earlier version of this README told people to copy a
four-line caller into each repository — unnecessary work caused by a wrong reading of the docs.

The workflow runs on `opened`, `edited`, `reopened` and `synchronize`. `edited` matters: without it,
fixing the description after a failure leaves the check red, and deleting the evidence after a success
leaves it green.

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
