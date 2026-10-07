# Specs

One living spec per area, in this directory. A change to code, configuration
or tests starts by editing the spec it touches, in the same merge request, as
its first commit.

Header of every spec:

```
Status: Draft | Approved | As-built | Superseded by <file>
Code: <paths this spec governs>
Verified against: main @ <commit>
```

Order: problem and decisions first, then one section per technical subject
holding its design, requirements and edge cases, then verification, open
questions and the implementation inventory.

IDs carry the area prefix of the spec (`ARENA-3`) and are never renumbered or
reused; a split requirement keeps its ID for the first part and adds a suffix
for the rest (`ARENA-3a`). Decisions are `DEC-n`, open questions `OQ-n`,
acceptance criteria `AC-n`, all scoped to their spec.

Every requirement names its check and origin:

- `Test:` the check that fails on a violation: a test scenario, a CI job or,
  prefixed `manual:`, a runbook step. `none` is a listed gap.
- `Since:` the merge request or commit that introduced the behaviour,
  `not implemented`, or `not met yet (<issue>)`.

MUST and MUST NOT are absolute, SHOULD holds unless a documented reason says
otherwise, MAY is left to the implementer.
