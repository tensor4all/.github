## What and why

<!-- One paragraph. What changes, and the problem it removes. Link the issue it closes. -->

## Verification

<!--
Required. A reviewer merges on this section, not on "CI is green" — this
repository has merged green PRs whose test never ran, whose `cargo package`
only built, and whose threshold contradicted its own measurement.

Answer all three:

1. What would fail if this change were wrong?
2. Which command(s) did you actually run, and what did they print?
   Paste the lines. A summary is not evidence.
3. If you measured nothing, write `Not measured` and say why.
-->

```
# command(s) and their real output
```

## Claims ↔ evidence

<!--
Every number, "faster", "safer", "fixed", "same behaviour" in this description
needs a row. If a row says "not verified", say that in the description too —
do not let a claim stand on reasoning alone.
-->

| Claim in this description | Evidence |
|---|---|
|  |  |

## Scope

- [ ] No public API change
- [ ] Public API change, and the `## Breaking` entry is in `CHANGELOG.md`
- [ ] Touches `.github/` or `scripts/` (a reviewer merges these, not a bot)

---

<!--
If you are an AI agent: read `AGENTS.md` in this repository first, and open an
issue before implementing a feature. Bug-fix PRs are welcome without one.
-->
