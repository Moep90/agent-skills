# Arena: cross-model author and review loop

```text
Status: Approved
Code: plugins/arena/
Verified against: not yet (no implementation)
```

## Problem

Improving an artifact (code, a Claude Code skill, a piece of text) with two
model families currently means copying it by hand between Claude and ChatGPT:
one writes, the other reviews, the result goes back, until both rate it 9.5 or
higher. The copying is the cost, and the stop rule is unreliable: a model
rates its own output more leniently than others do, and a reviewer that sees
its earlier feedback addressed tends to raise its score whether or not the
artifact improved.

Arena automates that loop inside a coding agent (Claude Code, Codex CLI or
OpenCode). One model family writes, the other reviews in a fresh context
against a fixed rubric, and the loop stops on an explicit verdict or hands
over to the user.

## Decisions

DEC-1: Codex is driven through the official Codex CLI (`codex exec`), logged
in with the user's ChatGPT Plus account, not through browser automation of
chatgpt.com. OpenAI's Terms of Use forbid automatically or programmatically
extracting output, and the web UI changes without notice. Plus includes the
Codex CLI with a 5-hour usage window (15 to 150 messages for GPT-6 Sol per
OpenAI's pricing page, October 2026) plus an unpublished weekly limit. A
review round is one message, so three rounds per artifact fit comfortably. In
the default direction code writing stays on the Claude subscription.

DEC-2: Arena is one thin skill that calls `codex exec` and `claude -p`
directly.
OpenAI's `codex-plugin-cc` reviews only git changes and has a code-oriented
prompt. Its optional review gate re-runs a review on every Claude stop, but
has no round cap or verdict-based end and its own documentation warns that it
can drain usage limits quickly. `claudex-loop` covers both directions but runs a
four-phase plan process that is oversized for a skill or a paragraph of text.
Both were evaluated as reuse candidates.

DEC-3: The loop stops on a reviewer verdict against a frozen rubric, with a
hard cap of three reviews, not on scores. The reviewer contract has no score
field. Published measurements of iterative refinement
put most of the gain in the first two rounds and saturation around the third.

DEC-4: Every review runs in a fresh context and receives a ledger of earlier
findings instead of resuming the reviewer's session. This avoids session-ID
handling and the leniency drift of a reviewer that remembers its own earlier
feedback; the cost is re-reading the artifact each round.

DEC-5: Both directions ship in v1: Claude writes and Codex reviews, and Codex
writes and a fresh headless Claude reviews.

DEC-6: Arena runs on three hosts: Claude Code, Codex CLI and OpenCode. All
three read the Agent Skills `SKILL.md` format. Hermes Agent is excluded.
Hermes also supports cloud providers, but this project assumes it is used
with local models so that the content it processes stays on the machine, and
Arena exists to send content to OpenAI and Anthropic. A variant with two
local model families would be a different product.

Distribution, manifests and versioning are specified in
[marketplace.md](marketplace.md).

Related: [OpenAI Codex pricing](https://learn.chatgpt.com/docs/pricing),
[OpenAI Terms of Use](https://openai.com/policies/terms-of-use/),
[codex-plugin-cc](https://github.com/openai/codex-plugin-cc),
[claudex-loop](https://github.com/chaseai-yt/claudex-loop),
[self-preference bias in rubric evaluation](https://arxiv.org/abs/2604.06996),
[iterative self-repair rounds](https://arxiv.org/abs/2604.10508)

## Invocation and roles

The skill lives in `plugins/arena/skills/arena/SKILL.md`; installation per host
is specified in [marketplace.md](marketplace.md). It has no script and no
runtime dependency apart from `git` and the CLIs a run calls (`codex`,
`claude`); it runs only inside a git working tree (ARENA-19a).

The host is the agent that runs the skill and orchestrates the loop. The
author is the host session itself when `--author` names the host's own model
family; otherwise the author is a CLI process of the named family. The
reviewer is always a fresh CLI process of the other family. On Claude Code
with the default author, the session writes and `codex exec` reviews; on
Codex CLI the mirror image holds. On OpenCode the host model's family decides;
when it is neither Claude nor GPT, the author always runs as a CLI process.

- ARENA-1a: Every Codex call MUST set model and reasoning effort explicitly
  with `-m <model> -c model_reasoning_effort=<effort>`, using the values in
  the implementation inventory.

  The user's global Codex default does not apply. A measured comparison on
  this spec: `gpt-6-luna` (the global default at the time) approved it after
  three rounds; a single fresh `gpt-6.1-sol` review at medium effort then
  found five blocking gaps. Two Sol medium reviews of this spec used about
  33k to 39k tokens and 3% to 4% of the Plus 5-hour window each; the weekly
  meter moved by 1% for both together. A review-only run makes at most six
  reviewer calls (ARENA-14), typically three or fewer, so it stays within a
  few percent of the weekly quota. Codex author calls in the reverse
  direction write instead of read and are not measured yet. Codex's model catalog
  lists `gpt-6.1-sol` as the latest workhorse model and `gpt-5.6-sol` as an
  older generation.

  - Test: tests/run.sh approved (AC-1, the stub records its arguments)
  - Since: this change

- ARENA-1: The skill MUST be invocable as
  `arena <task or path> [--author claude|codex] [--rubric code|skill|text]`,
  through the host's skill invocation: `/arena:arena` in Claude Code when
  installed as a plugin (Claude Code namespaces plugin skills), `/arena` in
  Claude Code for a standalone skill and in OpenCode, `$arena` in Codex CLI. `--author` defaults to the host model's family. When
  the host model is neither Claude nor GPT and `--author` is missing, the
  skill MUST stop before the preflight and ask for it.

  The round cap is not a flag (ARENA-14). A flag is added once three rounds
  prove wrong in use.

  - Test: tests/run.sh approved (AC-1); manual: AC-11 (partial: Claude model on OpenCode not run)
  - Since: this change

- ARENA-1b: A run on a path that already exists MUST start with a review; a
  run on a task MUST start with the author writing the target.

  An existing artifact is what the user wants judged, so round 1 reviews it
  as it is. Starting with the author would also make a CLI author that
  sees nothing to change hit the ARENA-22 stop before any review.

  - Test: tests/run.sh approved (AC-1, first call is a review); manual: AC-8
  - Since: this change

- ARENA-2: The author and the reviewer of a run MUST come from different model
  families.

  With `--author claude` Claude writes and Codex reviews; with
  `--author codex` Codex writes and Claude reviews. Who runs in-session and
  who as a CLI process follows from the host, as described above.

  - Test: tests/run.sh approved (AC-1); manual: AC-8, AC-11 (partial: Claude model on OpenCode not run)
  - Since: this change

- ARENA-3: A Codex reviewer MUST run as `codex exec --sandbox read-only`.

  - Test: tests/run.sh approved (AC-1, the stub records its arguments)
  - Since: this change

- ARENA-4: A Codex author that is not the host MUST run as
  `codex exec --sandbox workspace-write`.

  - Test: manual: AC-8
  - Since: this change

- ARENA-4a: A Claude author that is not the host MUST run as
  `claude -p --tools Read,Grep,Glob,Edit,Write,Bash --allowedTools Read Grep Glob Edit Write 'Bash(git rm:*)' 'Bash(git mv:*)' --strict-mcp-config --no-session-persistence --permission-mode dontAsk`.

  The author needs to delete and rename files for ordinary code revisions,
  which Edit and Write cannot do, so Bash is available but only `git rm` and
  `git mv` are allowed. Probes with Claude Code 2.1.292 in a fresh git
  directory: with `--permission-mode acceptEdits` an unlisted `touch` still
  ran, because that mode approves simple file commands; with `dontAsk` and
  this allowlist, `git mv`, `git rm` and Write ran and `touch` was denied.

  - Test: manual: AC-10
  - Since: this change

- ARENA-5: A Claude reviewer MUST run as
  `claude -p --tools Read,Grep,Glob --strict-mcp-config --no-session-persistence`
  with the review prompt on stdin.

  A separate process starts with an empty context; the orchestrating session
  does not, so it cannot serve as a fresh reviewer. A subagent spawned with
  the Agent tool would inherit the full tool set unless a custom agent
  definition were installed next to the skill. A probe with Claude Code
  2.1.292 showed that `--tools` alone still leaves every configured MCP tool
  available; with `--strict-mcp-config` added, the process reports exactly
  Glob, Grep and Read.

  - Test: manual: AC-8
  - Since: this change

- ARENA-6: Every review MUST run in a fresh context: a new `codex exec` call or
  a new `claude -p` process. Session resume MUST NOT be used.

  - Test: tests/run.sh cap (AC-2, no `resume` argument across three calls)
  - Since: this change

- ARENA-7: The host session MUST NOT judge the artifact's
  quality itself. It enforces the protocol and relays verdicts.

  - Test: tests/run.sh approved (AC-1, the reported verdict is the stub's)
  - Since: this change

## Rubrics

A rubric is a short list of criteria per artifact type, written into the
skill. Before round 1 the skill shows the inferred type and its criteria; the
user confirms and may add task-specific criteria such as acceptance criteria
or a style guide.

| Type | Criteria |
|---|---|
| `code` | Correct including edge cases. No security issue. Meets the task and its acceptance criteria. Tests cover the changed behaviour. No scope beyond the task. |
| `skill` | The trigger description matches when the skill should be used. Instructions are unambiguous and executable. No contradictions. Serves the stated purpose and nothing beyond it. |
| `text` | Claims are correct or marked as assumptions. Serves its purpose for the stated audience. No contradictions or repetition. Concrete instead of generic. |

- ARENA-8: The rubric MUST be confirmed by the user before the first review.

  Passing both the target path and `--rubric` in the invocation counts as
  confirmation; the skill then starts without asking. This is also how the
  headless tests, which have no stdin, get past the confirmation.

  - Test: manual: AC-7; tests/run.sh approved (AC-1, no question asked)
  - Since: this change

- ARENA-8a: Every run MUST have one target path, a file or a directory,
  confirmed by the user together with the rubric.

  For a path invocation the target is that path. For a task invocation the
  skill proposes where the artifact will be written. ARENA-22 and ARENA-23
  measure against this path.

  - Test: manual: AC-7, AC-8
  - Since: this change

- ARENA-9: The rubric MUST NOT change after the first review of a run.

  A reviewer that could add criteria mid-run would move the goal and defeat
  the round cap.

  - Test: none
  - Since: this change

- ARENA-10: For rubric `code`, the orchestrating session MUST run the
  project's tests and linter before each review and record the result in the
  ledger.

  The reviewer is read-only and judges against real results instead of
  guessing whether the code runs. The orchestrator runs them rather than the
  author, so a review-first run (ARENA-1b) needs no author call before its
  first review and ARENA-22 never sees a validation-only call. Failing tests
  or lint do not stop the run; they are evidence for the reviewer. If the
  checks cannot be executed at all, the ledger records that with the error
  and the review proceeds.
  The last 50 lines of the output also go into the review prompt, because a
  `claude -p` reviewer may not be able to read files under `/tmp`.

  - Test: none
  - Since: this change

## Ledger and reviewer contract

The ledger is a plain file in a run directory created with `mktemp -d`. The
reviewer emits one line per finding with five fields. The first field is
`new` for a new finding, or the ledger ID of the entry it repeats. The fifth field runs to the end of the
line and may contain `|`:

```text
new | blocking | criterion: correct | src/x.py:42 | <problem and suggested fix>
```

The orchestrating session replaces `new` with the next free ID
`R<round>-F<n>`. The author copies each line into the ledger and appends
status and note:

```text
R1-F2 | blocking | criterion: correct | src/x.py:42 | <problem and suggested fix> | status: rejected | <reason>
```

Status is `open`, `fixed` or `rejected`. The reviewer receives the task as
stated in the invocation and the confirmation step (including audience and
acceptance criteria where given), the rubric, the ledger and the artifact
path. Without the task it could not judge criteria such as "meets the task"
or "serves its purpose for the stated audience". It re-checks every `fixed` entry and may add new
findings. Every line the reviewer emits is an open finding: emitting an
existing ID marked `fixed` means it is not fixed, emitting an existing ID
marked `rejected` is a reopen (ARENA-18). The reviewer reports findings only
and never edits the artifact.

- ARENA-11c: Finding IDs MUST be assigned by the orchestrating session. A
  first field that is neither `new` nor an existing ledger ID MUST be
  treated as a contract violation under ARENA-21.

  Assigning IDs centrally makes collisions impossible. A reviewer that
  restates a rejected finding as `new` instead of with its ID would still
  bypass ARENA-18; the orchestrator cannot detect that, so it relies on the
  review prompt and is checked by AC-9. This replaces an earlier draft in
  which the reviewer allocated IDs itself.

  - Test: tests/run.sh contract (AC-4, unknown-ID variant); manual: AC-9
  - Since: this change

- ARENA-11: Reviewer output MUST start with the line
  `VERDICT: APPROVED`, `VERDICT: REVISE` or `VERDICT: BLOCKED`, followed only
  by finding lines in the five-field format.

  `BLOCKED` means the reviewer needs a decision only the user can make.

  - Test: tests/run.sh contract (AC-4)
  - Since: this change

- ARENA-11a: `VERDICT: APPROVED` together with a blocking finding MUST be
  treated as a contract violation under ARENA-21.

  - Test: tests/run.sh contract (AC-4)
  - Since: this change

- ARENA-11b: `VERDICT: REVISE` without any blocking finding MUST be treated
  as a contract violation under ARENA-21.

  Without this rule a third-round `REVISE` with only minor findings would
  have no defined end.

  - Test: tests/run.sh contract (AC-4)
  - Since: this change

- ARENA-12: A finding MUST be treated as `blocking` only if it names a rubric
  criterion and a location; any other finding is `minor`.

  Style and taste are minor by definition. This keeps the loop from chasing
  preferences.

  - Test: none
  - Since: this change

- ARENA-13: Before the next review the author MUST mark every open blocking
  finding `fixed`, or `rejected` with a reason.

  Findings are input, not truth. A rejection with a reason is a valid answer
  and goes to the reviewer in the next ledger. A CLI author receives the
  ledger with its task and ends its reply with one line per open blocking
  finding, `<ID> | fixed` or `<ID> | rejected | <reason>`; the orchestrating
  session copies these into the ledger.

  - Test: manual: AC-7
  - Since: this change

## Stop conditions

- ARENA-14: A run MUST perform at most three reviews.

  A contract retry under ARENA-21 repeats the same review and does not count
  as a review. A run therefore makes at most six reviewer calls; the first
  version of this spec left open whether a violation in round three could be
  retried.

  - Test: tests/run.sh cap (AC-2)
  - Since: this change

- ARENA-15: A run MUST stop and report the artifact and the minor findings
  when a review returns `APPROVED` and no blocking finding is open.

  - Test: tests/run.sh approved (AC-1)
  - Since: this change

- ARENA-16: A run MUST stop and hand over to the user when a review returns
  `BLOCKED`.

  - Test: tests/run.sh blocked (AC-6)
  - Since: this change

- ARENA-17: A run MUST hand over to the user with the ledger when the third
  review still leaves a blocking finding open.

  - Test: tests/run.sh cap (AC-2)
  - Since: this change

- ARENA-18: A run MUST hand over to the user immediately when a reviewer
  raises a finding again that the author rejected.

  In model debates the more persuasive side tends to win, not the correct one,
  so a disputed finding goes to the user instead of another round of argument.
  A `fixed` finding the reviewer sets back to `open` is not a reopen; it stays
  in the loop and counts against ARENA-14.

  - Test: manual: AC-9
  - Since: this change

## Failure handling

Failures stop the run and are reported; Arena never retries in a loop. The one
exception is a broken output contract, which is often transient.

- ARENA-19: Before any other work the skill MUST check the login of every CLI
  the run will call and stop with the remedy command if one is not logged in.

  `codex login status` must exit 0; `claude auth status` must exit 0 and
  report `"loggedIn": true` in its JSON output.

  No run directory exists at this point, so this stop reports only the
  failure and the remedy; ARENA-24 does not apply.

  - Test: tests/run.sh preflight (AC-5)
  - Since: this change

- ARENA-19a: As part of the preflight the skill MUST stop unless
  `git rev-parse --is-inside-work-tree` exits 0 and prints exactly `true`.

  Inside `.git` the command exits 0 and prints `false`, so the exit code
  alone is not enough.

  Change detection (ARENA-23) needs a work tree, and Codex refuses to run outside a
  repository unless given `--skip-git-repo-check`. Supporting non-git
  directories would need both a second detection method and that flag; no
  use case asks for it.

  - Test: tests/run.sh nogit (AC-5)
  - Since: this change

- ARENA-20: An author or reviewer call (`codex exec` or `claude -p`) that
  exits non-zero or runs longer than ten minutes MUST stop the run without
  retry and report an excerpt of its stderr.

  This covers the 5-hour and weekly Plus limits. `codex exec` exits 1 on a
  failed turn and prints `ERROR: <message>` to stderr; for a usage limit the
  message starts with `You’ve hit your usage limit` (typographic apostrophe)
  and ends with `Try again at <time>.` when the reset time is known. The
  report quotes that line, so the user sees the reset time. Exit code and
  stderr decide the stop; matching the message text only selects what to
  quote. Ten minutes is the limit of a single Bash call in Claude Code.

  Related: `codex-rs/protocol/src/error.rs` and
  `codex-rs/exec/src/event_processor_with_human_output.rs` in
  [openai/codex](https://github.com/openai/codex), read for codex-cli 0.160.1

  - Test: tests/run.sh ratelimit (AC-3) (partial: a failing or hanging `claude -p` reviewer is not covered)
  - Since: this change

- ARENA-21: A review that breaks the contract of ARENA-11, ARENA-11a or
  ARENA-11b MUST be repeated exactly once with a reminder of the contract; a
  second violation of the same review MUST stop the run.

  - Test: tests/run.sh contract (AC-4)
  - Since: this change

- ARENA-22: A CLI author run that leaves the target unchanged MUST stop the
  run, unless it marks every open blocking finding `rejected`.

  Detected by comparing a content hash of the target path (ARENA-8a) before
  and after. In the first round there are no findings, so an unchanged
  target always stops; in later rounds a rejection-only revision is a valid
  answer under ARENA-13 and goes to the next review.

  - Test: manual: AC-8
  - Since: this change

- ARENA-23: After a CLI author run, every detected change outside the
  target MUST be reported to the user with the list of files, without
  reverting them.

  Detection: a marker file is created right before the author call. Afterwards
  every file below the working directory, ignored files included and `.git`
  excluded, that is newer than the marker and outside the target counts as
  changed. Deletions are found by comparing
  `git status --porcelain --ignored --untracked-files=all` before and after;
  without `--untracked-files=all` git collapses an untracked directory into
  one line and a deleted file inside it would go unnoticed. Known gap: deleting a file inside an already ignored
  directory is not detected, because git reports only the directory. A full
  before-and-after inventory of every file would close the gap but costs a
  scan of directories such as `node_modules` on every round.
  Reverting could destroy work the user wants; the user decides.

  - Test: manual: AC-8
  - Since: this change

- ARENA-24: Every stop after the run directory exists MUST report the artifact path, the
  ledger path and the round number, and keep the run directory.

  A stopped run is not resumable. Running `/arena` again on the same path
  starts a new run on the current state.

  - Test: tests/run.sh cap (AC-2)
  - Since: this change

- ARENA-27: The skill MUST refuse to run when the host is Hermes Agent.

  The skill states this as its first instruction. Arena is also not
  published to Hermes' skill directory, so the refusal only matters for a
  manual copy.

  - Test: manual: AC-12
  - Since: not met yet (manual AC-12 pending)

## Data exposure

The Codex sandbox limits writes, not reads: in `read-only` and
`workspace-write` mode Codex can read any file the user can read, not only the
working directory. `claude -p` with `Read`, `Grep` and `Glob` is not confined
to the working directory either. Whatever either CLI actually reads enters the
model context and goes to OpenAI or Anthropic. In practice it reads what the prompt points to and what it
searches for, which is mostly the working directory. Arena does not filter
content; only the user can judge what may leave the machine.

- ARENA-25: The skill description MUST state that the CLIs it calls can read
  any file the user can read and that everything they read is sent to OpenAI
  or Anthropic.

  - Test: manual: read `plugins/arena/skills/arena/SKILL.md` frontmatter
  - Since: this change

- ARENA-26: After the preflight and before the first author or reviewer
  call, the skill MUST ask the user to
  confirm when the working directory contains files matching `.env*`, `*.pem`,
  `*.key`, `id_rsa*` or `credentials*`.

  - Test: none
  - Since: this change

## Verification

Arena is a prompt, so its correctness is protocol compliance. Two layers check
it.

Paths in `Test:` lines and in this section are relative to `plugins/arena/`.

Layer 1 runs without Codex quota, on the Claude Code host only. A stub
`tests/bin/codex` answers
`login status` and `exec` from canned responses per scenario, and logs every
call with its arguments. `tests/run.sh <scenario>` creates a throwaway git
directory whose `.claude/skills/arena` links to `plugins/arena/skills/arena`, so the test
exercises the repository's skill rather than whatever is installed. It then
runs `claude -p "/arena <fixture> --rubric <type>" --permission-mode bypassPermissions
< /dev/null` there with `tests/bin` first on `PATH` and asserts on the stub's
call log and the final output. Each scenario costs one headless Claude run on
the user's subscription.

A probe with Claude Code 2.1.292 confirmed the mechanics this relies on: a
project-level skill is invoked by its slash command in `claude -p`, its Bash
calls resolve `codex` through the inherited `PATH`, and it can start further
processes. Without `< /dev/null` the run waits three seconds for stdin.

Layer 2 is manual with the real CLIs. It covers what the stub cannot force:
review quality, the Codex author direction, the reopen hand-over and the
Codex CLI and OpenCode hosts.
Neither layer proves the reviews are good; AC-7 and daily use are the only
evidence for that.

- AC-1 (ARENA-1, ARENA-1a, ARENA-1b, ARENA-2, ARENA-3, ARENA-7, ARENA-8, ARENA-15):
  invoked with target path and `--rubric`, the stub returns `APPROVED`.
  Exactly one `exec` call with `--sandbox read-only` and the inventory's model
  and effort; no confirmation question; the run reports the artifact.
  Check: `tests/run.sh approved`
- AC-2 (ARENA-6, ARENA-14, ARENA-17, ARENA-24): the stub always returns
  `REVISE` with one blocking finding. Exactly three `exec` calls, none with
  `resume`; the run hands over with artifact path, ledger path and round 3.
  Check: `tests/run.sh cap`
- AC-3 (ARENA-20): the stub exits 1 and prints
  `ERROR: You’ve hit your usage limit. Try again at 3:14 PM.` on stderr.
  Exactly one `exec` call; the report contains `Try again at 3:14 PM`.
  Check: `tests/run.sh ratelimit`
- AC-4 (ARENA-11, ARENA-11a, ARENA-11b, ARENA-11c, ARENA-21): five
  variants. In the first four the stub returns the same broken output on
  its first two calls: no `VERDICT:` line; `VERDICT: APPROVED` with a
  blocking finding; `VERDICT: REVISE` with only minor findings; a finding
  line with an unknown severity word (`urgent`). Each makes
  exactly two `exec` calls, then stops. In the fifth the stub returns a
  valid `REVISE` in round 1, then twice a round 2 review with a finding
  whose first field is an ID not in the ledger; it makes exactly three `exec` calls, then stops.
  Check: `tests/run.sh contract`
- AC-5 (ARENA-19, ARENA-19a): two variants. The stub fails `login status`;
  or the run starts in a directory that is not a git working tree. Each makes
  zero `exec` calls and reports the remedy.
  Check: `tests/run.sh preflight`, `tests/run.sh nogit`
- AC-6 (ARENA-16): the stub returns `BLOCKED`. Exactly one `exec` call, then
  hand-over.
  Check: `tests/run.sh blocked`
- AC-7 (ARENA-8, ARENA-8a, ARENA-13): `/arena tests/fixtures/skill-contradiction/SKILL.md`
  with the real Codex CLI. The rubric is shown for confirmation, the planted
  contradiction is reported as blocking, Claude fixes it, and the run ends
  `APPROVED` within three reviews.
  Check: manual
- AC-8 (ARENA-1b, ARENA-2, ARENA-4, ARENA-5, ARENA-8a, ARENA-22, ARENA-23): `/arena --author codex`
  on a short text task in a clean git checkout. Codex writes the target, a
  headless Claude reviews, and `git status` shows no file outside the target.
  Check: manual
- AC-9 (ARENA-11c, ARENA-18): during a real run, reject a blocking finding with a reason
  the reviewer will dispute. The run hands over after that review instead of
  starting another.
  Check: manual
- AC-10 (ARENA-1, ARENA-2, ARENA-4a, ARENA-5, ARENA-19): on the Codex CLI host,
  `$arena <path> --rubric text` reviews with `claude -p` and the restricted
  tool set; `$arena "<task>" --author claude --rubric text` writes the target
  with the restricted Claude author; a follow-up task that requires deleting
  and renaming a file under the target completes with `git rm` and `git mv`.
  The preflight checks `claude auth status`.
  Check: manual
- AC-11 (ARENA-1, ARENA-2): on OpenCode with a Claude model,
  `/arena <path> --rubric text` runs with the host as author and `codex exec`
  as reviewer and ends with a verdict. With a model that is neither Claude nor
  GPT, the same call without `--author` stops and asks for it; with
  `--author codex` it runs Codex as CLI author and Claude as reviewer.
  Check: manual
- AC-12 (ARENA-27): with the skill copied into Hermes Agent's skill directory,
  invoking it produces a refusal and no CLI call.
  Check: manual

## Open questions

None. OQ-1 (headless skill loading) was settled by a probe and OQ-2 (the
usage-limit message) from the Codex source; both are recorded under
Verification and ARENA-20.

## Implementation inventory

| Path | Purpose |
|---|---|
| `plugins/arena/skills/arena/SKILL.md` | The skill: host rules, protocol, rubrics, reviewer prompt, ledger format |
| `plugins/arena/tests/bin/codex` | Stub CLI: canned responses per scenario, call log with arguments |
| `plugins/arena/tests/scenarios/<name>/` | Canned stub responses and exit codes for `approved`, `cap`, `ratelimit`, `contract` (five variants), `preflight`, `nogit` (run outside git), `blocked` |
| `plugins/arena/tests/run.sh` | Runs one scenario headless in a throwaway git directory linking `.claude/skills/arena` to the skill, asserts on the call log and output |
| `plugins/arena/tests/fixtures/skill-contradiction/SKILL.md` | Skill with a planted contradiction for AC-7 |

| Value | Setting |
|---|---|
| Review cap | 3 per run |
| Contract retries | 1 |
| Codex model | `gpt-6.1-sol` |
| Codex reasoning effort | `medium` |
| Codex call timeout | 10 minutes |
| Secret file patterns | `.env*`, `*.pem`, `*.key`, `id_rsa*`, `credentials*` |
