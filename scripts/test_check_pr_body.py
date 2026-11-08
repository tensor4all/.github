#!/usr/bin/env python3
"""Tests for check_pr_body.py. Every case here is a bug that was shipped once.

Run: python3 scripts/test_check_pr_body.py

The cases marked "regression" come from an adversarial review of the first
version of this checker, which passed all eight cases I had tried by hand and
still let five wrong bodies through. That is the reason this file exists: a
validator whose own tests are not committed is a claim, not a check.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_pr_body import BAD, OK, check  # noqa: E402

TEMPLATE = (Path(__file__).resolve().parent.parent / "pull_request_template.md").read_text(encoding="utf-8")


class Accepts(unittest.TestCase):
    def test_command_and_output(self):
        code, msg = check("## Verification\n\n```\ncargo test -> 216 passed; 0 failed\n```\n")
        self.assertEqual(code, OK, msg)

    def test_filled_in_template_keeps_its_instructions(self):
        """regression: instructions left as HTML comments used to fail a real answer."""
        body = TEMPLATE.replace(
            "# command(s) and their real output",
            "cargo test -> 216 passed",
        )
        code, msg = check(body)
        self.assertEqual(code, OK, msg)

    def test_wildcard_fence(self):
        """regression: ~~~ fences were not recognised."""
        code, msg = check("## Verification\n\n~~~sh\npytest\n1 passed\n~~~\n")
        self.assertEqual(code, OK, msg)

    def test_not_measured_with_reason(self):
        code, msg = check("## Verification\n\nNot measured: this only renames a private helper.\n")
        self.assertEqual(code, OK, msg)

    def test_output_block_containing_a_heading(self):
        """regression: a `## ` line inside a fence used to end the section early."""
        body = "## Verification\n\n```\n## Sub-heading printed by the tool\nthen 3 passed\n```\n"
        code, msg = check(body)
        self.assertEqual(code, OK, msg)

    def test_opt_out_with_reason(self):
        code, msg = check("## Verification\n\n<!-- skip-verification-check: reviewer approved verbally -->\n")
        self.assertEqual(code, OK, msg)


class Rejects(unittest.TestCase):
    def test_empty_body(self):
        self.assertEqual(check("")[0], BAD)

    def test_no_section(self):
        self.assertEqual(check("## What\n\nfixed it\n")[0], BAD)

    def test_template_untouched(self):
        """regression: this is the normal failure mode and must not pass."""
        self.assertEqual(check(TEMPLATE)[0], BAD)

    def test_section_present_but_empty(self):
        self.assertEqual(check("## Verification\n\n## Scope\n\n- [x] No public API change\n")[0], BAD)

    def test_comment_only(self):
        self.assertEqual(check("## Verification\n\n<!-- TODO -->\n")[0], BAD)

    def test_language_tag_is_not_evidence(self):
        """regression: an empty ```bash fence passed because the tag counted."""
        self.assertEqual(check("## Verification\n\n```bash\n```\n")[0], BAD)

    def test_comment_only_inside_tagged_fence(self):
        """regression: a fence holding one comment line passed when tagged."""
        self.assertEqual(check('## Verification\n\n```bash\n# nothing ran\n```\n')[0], BAD)

    def test_whole_section_hidden_in_a_comment(self):
        """regression: an invisible section used to pass."""
        body = "<!--\n## Verification\n```\npytest\n```\n-->"
        self.assertEqual(check(body)[0], BAD)

    def test_blank_opt_out_reason(self):
        """regression: `skip-verification-check:   ` passed with no reason."""
        self.assertEqual(check("## Verification\n\n<!-- skip-verification-check:   -->\n")[0], BAD)

    def test_not_measured_without_reason(self):
        self.assertEqual(check("## Verification\n\nNot measured\n")[0], BAD)


if __name__ == "__main__":
    unittest.main(verbosity=2)
