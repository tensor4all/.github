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

  * a `## Verification` heading (level 2, case-insensitive) that is **visible** —
    a heading inside an HTML comment does not count, and
  * inside it, either
      - a fenced code block (``` or ~~~) whose content has at least one line
        that is neither blank nor a full-line comment, and which is not just the
        fence's language tag, or
      - `Not measured` followed by at least three words of reason, or
  * an explicit opt-out `<!-- skip-verification-check: <two or more words> -->`,
    which a human reviewer must see and accept.

Matching happens **after** removing HTML comments. The template's instructions
are comments, so "the author left them alone" and "the author wrote nothing" are
indistinguishable unless the comments come out first — and a filled-in template
must not be punished for keeping those instructions.

Run the tests with: `python3 scripts/test_check_pr_body.py`

Usage:
    python3 check_pr_body.py --body-file body.md
    PR_BODY="$(gh pr view 12 --json body -q .body)" python3 check_pr_body.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys

OPT_OUT = re.compile(r"<!--\s*skip-verification-check:\s*(.*?)\s*-->", re.IGNORECASE | re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
# GitHub renders an unclosed `<!--` as a comment to end of input; a regex that
# needs `-->` therefore sees text the reviewer never sees.
HTML_COMMENT_UNCLOSED = re.compile(r"<!--(?:(?!-->).)*$", re.DOTALL)
NOT_MEASURED = re.compile(r"not\s+measured\b(.*)", re.IGNORECASE)
HEADING_VERIFICATION = re.compile(r"^##\s*verification\s*$", re.IGNORECASE)
FENCE_OPEN = re.compile(r"^(```+|~~~+)\s*(\S*)\s*$")

# Visible text that only appears when the template was pasted back unchanged.
PLACEHOLDER_MARKERS = (
    "Required. A reviewer merges on this section",
    "What would fail if this change were wrong?",
    "command(s) and their real output",
)

OK, BAD = 0, 1


def strip_comments(text: str) -> str:
    """Remove HTML comments, preserving the line structure around them."""
    out = HTML_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return HTML_COMMENT_UNCLOSED.sub(lambda m: "\n" * m.group(0).count("\n"), out)


def scan(text: str) -> tuple[list[tuple[int, int, str]], list[tuple[int, int]]]:
    """Locate fenced blocks and level-2 headings, headings only outside fences.

    A pasted output block that contains a `## something` line must not terminate
    the section, so fences are tracked first and headings are collected only when
    no fence is open.
    """
    lines = text.splitlines(keepends=True)
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln)

    fences: list[tuple[int, int, str]] = []
    headings: list[tuple[int, int]] = []
    opening: tuple[str, int, str] | None = None

    for idx, ln in enumerate(lines):
        stripped = ln.strip()
        if opening is None:
            m = FENCE_OPEN.match(stripped)
            if m:
                opening = (m.group(1), idx, m.group(2))
                continue
            # Only a level-2 heading ends a level-2 section. `### Commands` is a
            # subsection of `## Verification` in GitHub's rendering, so it must
            # not terminate the scan.
            if re.match(r"^##\s+\S", stripped) and not stripped.startswith("###"):
                headings.append((offsets[idx], offsets[idx] + len(ln)))
        else:
            char, start_idx, info = opening
            if stripped.startswith(char) and stripped.strip(char[0]) == "":
                fences.append((offsets[start_idx], offsets[idx] + len(ln), info))
                opening = None

    if opening is not None:  # unterminated fence: runs to the end of the body
        char, start_idx, info = opening
        fences.append((offsets[start_idx], len(text), info))

    return fences, headings


def evidence_lines(fence_text: str, info: str) -> list[str]:
    """Content lines of a fence, without the fence markers or the language tag."""
    body = fence_text.splitlines()[1:]  # drop the opening ```/~~~ line and its tag
    if body and body[-1].strip().strip("`~") == "":
        body = body[:-1]  # drop the closing fence
    out = []
    for ln in body:
        s = ln.strip()
        if not s or s.startswith("#") or s == info:
            continue
        out.append(s)
    return out


def check(body: str) -> tuple[int, str]:
    if not body or not body.strip():
        return BAD, "The pull request body is empty. Say what you changed and how you verified it."

    opt = OPT_OUT.search(body)
    if opt:
        reason = opt.group(1).strip()
        if len(reason.split()) < 2:
            return BAD, ("The `skip-verification-check` opt-out needs a reason of two words or more. "
                         "An empty opt-out is not a decision a reviewer can weigh.")
        return OK, f"Verification check skipped by the author: {reason}"

    visible = strip_comments(body)
    fences, headings = scan(visible)

    ver = None
    for start, end in headings:
        if HEADING_VERIFICATION.match(visible[start:end].strip()):
            ver = (start, end)
            break
    if ver is None:
        return BAD, ("No visible `## Verification` section. State the command you ran and its real "
                     "output, or write `Not measured` and why. A heading inside an HTML comment does "
                     "not count: a reviewer cannot see it.")

    # `>=`, not `>`: `## Verification\n## Scope` puts the next heading exactly at the
    # end of the first, and `>` would let Scope's content count as verification.
    following = [h for h in headings if h[0] >= ver[1]]
    sec_start = ver[1]
    sec_end = following[0][0] if following else len(visible)
    section = visible[sec_start:sec_end]

    leftover = [p for p in PLACEHOLDER_MARKERS if p in section]
    if leftover:
        return BAD, ("The `## Verification` section still contains the template's placeholder text. "
                     "Replace it with what you actually ran; submitting the template unchanged is not "
                     "a verification.")

    for f_start, f_end, info in fences:
        if f_start >= sec_start and f_end <= sec_end:
            lines = evidence_lines(visible[f_start:f_end], info)
            if lines:
                return OK, f"Evidence found in a code block ({len(lines)} line(s))."

    nm = NOT_MEASURED.search(section)
    if nm and len(nm.group(1).split()) >= 3:
        return OK, "`Not measured` accepted, with a reason."

    return BAD, ("The `## Verification` section has no evidence: no code block with a command and no "
                 "`Not measured` with a reason. A reviewer needs to know what would have failed if "
                 "this change were wrong.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--body-file")
    args = ap.parse_args()

    if args.body_file:
        with open(args.body_file, encoding="utf-8") as fh:
            body = fh.read()
    else:
        body = os.environ.get("PR_BODY", "")

    code, message = check(body)
    print(f"::{'notice' if code == OK else 'error'}::{message}")
    return code


if __name__ == "__main__":
    sys.exit(main())
