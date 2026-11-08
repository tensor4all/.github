#!/usr/bin/env python3
"""Reject a pull request whose body does not say how the change was verified.

Why this exists: across this organization we merged PRs that were green because
a test never ran (a shell function used as a command, exit 127), because
`cargo package` verifies a build and not a test run, because a mutation of the
changed line still passed, and because a threshold contradicted the measurement
quoted next to it. In each case CI was green and the description claimed
something the artifact did not support. The fix that survives attention going
elsewhere is to make the description state its evidence, and to check it.

Contract (what passes):

  * a `## Verification` heading (level 2, case-insensitive), and
  * inside it, either
      - a fenced code block containing at least one line that is neither blank
        nor an HTML comment nor the template's placeholder, or
      - the words `Not measured` plus something after them (why), or
  * the body explicitly opts out with `<!-- skip-verification-check: <reason> -->`
    which a human reviewer must see and accept.

What fails, and why it is not pedantry: an untouched template is the normal
failure. The placeholder text is written as an HTML comment so it does not
render, which means "the author left it alone" is indistinguishable from "the
author wrote nothing" unless we look for the comment itself.

Usage:
    python3 check_pr_body.py --body-file body.md
    PR_BODY="$(gh pr view 12 --json body -q .body)" python3 check_pr_body.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys

HEADING = re.compile(r"^##\s*verification\s*$", re.IGNORECASE | re.MULTILINE)
ANY_H2 = re.compile(r"^##\s+", re.MULTILINE)
FENCE = re.compile(r"```.*?```", re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
OPT_OUT = re.compile(r"<!--\s*skip-verification-check:\s*(.+?)\s*-->", re.IGNORECASE | re.DOTALL)
NOT_MEASURED = re.compile(r"not measured\b[^\n]{0,200}", re.IGNORECASE)

# Text that only appears when the template was submitted untouched.
PLACEHOLDER_MARKERS = (
    "Required. A reviewer merges on this section",
    "What would fail if this change were wrong?",
    "command(s) and their real output",
)

OK, BAD = 0, 1


def section(body: str, start: int) -> str:
    """The text between the `## Verification` heading and the next `## `."""
    m = ANY_H2.search(body, start)
    return body[start : m.start()] if m else body[start:]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file")
    args = ap.parse_args()

    if args.body_file:
        with open(args.body_file, encoding="utf-8") as fh:
            body = fh.read()
    else:
        body = os.environ.get("PR_BODY", "")

    if not body.strip():
        print("::error::The pull request body is empty. Say what you changed and how you verified it.")
        return BAD

    opt = OPT_OUT.search(body)
    if opt:
        print(f"::notice::Verification check skipped by the author: {opt.group(1)}")
        return OK

    m = HEADING.search(body)
    if not m:
        print("::error::No `## Verification` section. State the command you ran and its real output, "
              "or write `Not measured` and why. See the organization default template.")
        return BAD

    sec = section(body, m.end())

    leftover = [p for p in PLACEHOLDER_MARKERS if p in sec]
    if leftover:
        print("::error::The `## Verification` section still contains the template's placeholder text. "
              "Replace it with what you actually ran. Submitting the template unchanged is not a "
              "verification.")
        return BAD

    # A fenced block whose visible content is not only comments counts as evidence.
    for block in FENCE.findall(sec):
        inner = HTML_COMMENT.sub("", block[3:].rsplit("```", 1)[0])
        lines = [ln for ln in (l.strip() for l in inner.splitlines()) if ln and not ln.startswith("#")]
        # A fence that only repeats the placeholder command hint is not evidence.
        if lines and "command(s) and their real output" not in " ".join(lines):
            print(f"::notice::Evidence found in a code block ({len(lines)} line(s)).")
            return OK

    nm = NOT_MEASURED.search(HTML_COMMENT.sub("", sec))
    if nm and len(nm.group(0).split()) > 2:
        print("::notice::`Not measured` accepted, with a reason.")
        return OK

    print("::error::The `## Verification` section has no evidence: no command block and no "
          "`Not measured` with a reason. A reviewer needs to know what would have failed if this "
          "change were wrong.")
    return BAD


if __name__ == "__main__":
    sys.exit(main())
