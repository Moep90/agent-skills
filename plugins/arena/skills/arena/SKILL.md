---
name: arena
category: workflow
description: >
  Cross-model author and review loop. One model family (Claude or Codex/GPT) writes or
  revises an artifact (code, a skill, a text), the other reviews it in a fresh CLI process
  against a frozen rubric, until the reviewer approves, three reviews are done, or a finding
  needs the user. Use when the user asks to have work reviewed or improved by the other
  model, to run arena, or to iterate a draft between Claude and Codex. The CLIs it calls
  (codex, claude) can read any file the user can read, and everything they read is sent to
  OpenAI or Anthropic.
---

# Arena

You are the host. You orchestrate the loop and enforce this protocol. You never judge the
artifact's quality yourself; verdicts come only from the reviewer. Follow the steps in order.

Fixed values: Codex model `gpt-6.1-sol`, reasoning effort `medium`, at most 3 reviews per
run, at most 1 contract retry per review, 590 seconds per call (below the 10-minute limit of one Bash call, so this timeout fires first). Never resume a CLI session.

## 0. Hermes Agent

If you are running inside Hermes Agent, reply "Arena does not run under Hermes Agent: it
sends content to OpenAI and Anthropic." and stop without running any command.

## 1. Parse the call

`arena <task or path> [--author claude|codex] [--rubric code|skill|text]`

- If the first argument is an existing path (file or directory), this is a **path run**: the
  target is that path and round 1 is a review. Otherwise it is a **task run**: the argument is
  the task, and the run starts with the author writing the target.
- Your family is `claude` if you are a Claude model, `codex` if you are a GPT/OpenAI model,
  otherwise `other`.
- The author family is `--author`, or your family if `--author` is missing. If your family is
  `other` and `--author` is missing, ask the user for `--author` and stop.
- The reviewer family is the other one of `claude` and `codex`.
- If the author family is your family, you are the author (in-session). Otherwise the author
  runs as a CLI process (section 6).

## 2. Preflight

Before any other command, check every CLI this run will call: the reviewer's, and the
author's if the author runs as a CLI process.

- codex: `codex login status` must exit 0. Otherwise stop with: "Codex is not logged in. Run
  `codex login`."
- claude: `claude auth status` must exit 0 and its output must contain `"loggedIn": true`.
  Otherwise stop with: "Claude is not logged in. Run `claude auth login`."

Then `git rev-parse --is-inside-work-tree` must exit 0 and print exactly `true`. Otherwise
stop with: "Arena runs only inside a git working tree. Run it from a git checkout."

A preflight stop reports only the cause and the remedy.

## 3. Confirm target, rubric and task

If the call names an existing target path and `--rubric`, that is the confirmation: do not
ask. Otherwise show the user, and wait for confirmation:

- the target path (for a task run, propose where the artifact will be written);
- the rubric type and its criteria (section 4); the user may add criteria;
- the task: for a task run the argument, for a path run its purpose, audience and acceptance
  criteria if the user gave them.

After confirmation the rubric is frozen for the whole run.

Then list sensitive files:

```bash
find . -path ./.git -prune -o \( -name '.env*' -o -name '*.pem' -o -name '*.key' \
  -o -name 'id_rsa*' -o -name 'credentials*' \) -type f -print
```

If anything is listed, show the list and ask whether to continue, because the CLIs can read
these files. Stop if the user does not confirm.

Create the run directory and remember its path as `RUN`:

```bash
RUN=$(mktemp -d) && : > "$RUN/ledger.md" && echo "$RUN"
```

Write the frozen rubric to `$RUN/rubric.md` and the task to `$RUN/task.md`.

## 4. Rubrics

| Type | Criteria (name: meaning) |
|---|---|
| `code` | correct: correct including edge cases. secure: no security issue. task: meets the task and its acceptance criteria. tested: tests cover the changed behaviour. scope: nothing beyond the task. |
| `skill` | trigger: the description matches when the skill should be used. clear: instructions are unambiguous and executable. consistent: no contradictions. scope: serves the stated purpose and nothing beyond it. |
| `text` | correct: claims are correct or marked as assumptions. purpose: serves its purpose for the stated audience. consistent: no contradictions or repetition. concrete: concrete instead of generic. |

If `--rubric` is missing, infer the type from the target and confirm it in section 3.

## 5. The loop

Keep a review counter `R`, starting at 0. A task run starts with an author step (section 6),
then reviews. A path run starts with a review.

### Review step

1. `R = R + 1`.
2. For rubric `code`: run the project's tests and linter (from its Makefile, package
   scripts or CI config), save the output to `$RUN/validation-$R.txt` and add one ledger line
   `VALIDATION review $R: <command> exited <code>, see validation-$R.txt`. Failing checks do
   not stop the run; they are evidence for the reviewer. If they cannot run, record the error
   the same way.
3. Write the review prompt (section 7) to `$RUN/review-$R.prompt`.
4. Call the reviewer, quoting paths:
   - Codex reviewer:
     `timeout 590 codex exec -m gpt-6.1-sol -c model_reasoning_effort=medium --sandbox read-only -o "$RUN/review-$R.md" - < "$RUN/review-$R.prompt" 2> "$RUN/review-$R.err"`
   - Claude reviewer:
     `timeout 590 claude -p --tools Read,Grep,Glob --strict-mcp-config --no-session-persistence < "$RUN/review-$R.prompt" > "$RUN/review-$R.md" 2> "$RUN/review-$R.err"`
5. If the call exits non-zero (124 means timeout), stop (section 8) without retry. Quote
   the stderr line that contains `usage limit` if there is one, because it carries the reset
   time; otherwise quote the last 5 lines of stderr.
6. Check the contract on `$RUN/review-$R.md`. It is broken when any of these holds:
   - the file is empty, or its first non-empty line is not exactly `VERDICT: APPROVED`,
     `VERDICT: REVISE` or `VERDICT: BLOCKED` (any text, code fence or heading before it
     counts as broken);
   - another non-empty line does not have exactly five fields separated by `|`: an ID that
     is `new` or an ID present in the ledger, `blocking` or `minor`, `criterion: <name>`,
     a location, the problem with a suggested fix;
   - the verdict is `APPROVED` and a line is `blocking`;
   - the verdict is `REVISE` and no line is `blocking`.
   On the first break, repeat this review once with the same `R`: append to the prompt
   "Your previous answer broke the output contract: `<reason>`. Answer again, following the
   contract exactly." On a second break of the same review, stop (section 8) and report the
   contract violation.
7. Record findings in the ledger. A `blocking` finding that names no rubric criterion or no
   location is recorded as `minor`. For each line:
   - `new`: append `R$R-F<n> | <severity> | criterion: <name> | <location> | <problem> | status: open |`
     with `<n>` counting from 1 within this review;
   - an ID whose status is `fixed`: set it back to `open` (the fix did not hold);
   - an ID whose status is `rejected`: the reviewer disputes a rejection. Stop now (section 8)
     and hand that finding to the user.
8. Act on the verdict:
   - `APPROVED`: stop (section 8) with success.
   - `BLOCKED`: stop and hand over; the reviewer needs a decision from the user.
   - `REVISE` and `R` is 3: stop and hand over with the open blocking findings.
   - `REVISE` otherwise: author step, then the next review.

## 6. Author step

The author handles every open blocking finding: fix it, or reject it with a reason.

**In-session author (you):** edit the target yourself, then set each open blocking finding
in the ledger to `status: fixed | <what changed>` or `status: rejected | <reason>`.

**CLI author:**

1. Write the author prompt (section 7) to `$RUN/author-$R.prompt`.
2. Snapshot before the call:

   ```bash
   touch "$RUN/marker-$R"
   git status --porcelain --ignored --untracked-files=all > "$RUN/status-before-$R"
   find "$TARGET" -type f -print0 2>/dev/null | sort -z | xargs -0 sha256sum 2>/dev/null | sha256sum > "$RUN/hash-before-$R"
   ```

3. Call the author:
   - Codex author:
     `timeout 590 codex exec -m gpt-6.1-sol -c model_reasoning_effort=medium --sandbox workspace-write -o "$RUN/author-$R.md" - < "$RUN/author-$R.prompt" 2> "$RUN/author-$R.err"`
   - Claude author:
     `timeout 590 claude -p --tools Read,Grep,Glob,Edit,Write,Bash --allowedTools Read Grep Glob Edit Write 'Bash(git rm:*)' 'Bash(git mv:*)' --strict-mcp-config --no-session-persistence --permission-mode dontAsk < "$RUN/author-$R.prompt" > "$RUN/author-$R.md" 2> "$RUN/author-$R.err"`
   A non-zero exit stops the run exactly like a failed review call.
4. Read the author's disposition lines at the end of its reply, `<ID> | fixed` or
   `<ID> | rejected | <reason>`, and update the ledger. A finding without a disposition
   stays `open`.
5. Compare the target hash with `$RUN/hash-before-$R`. If it is unchanged, stop (section 8)
   unless this is not the first author step and every open blocking finding is now
   `rejected`.
6. Find changes outside the target:

   ```bash
   find . -path ./.git -prune -o -type f -newer "$RUN/marker-$R" -print
   git status --porcelain --ignored --untracked-files=all | diff "$RUN/status-before-$R" - | grep '^[<>]'
   ```

   Every listed file outside the target goes into the final report. Never revert them.

Then do the next review step.

## 7. Prompt templates

Review prompt (fill in the parts in angle brackets):

```text
You are an independent reviewer. Review the artifact at <target path>. Do not edit any file.
Report findings only.

Task of the artifact: <content of task.md>

Rubric (frozen; judge only against these criteria):
<content of rubric.md>

Ledger of earlier findings (may be empty). Check every entry with status `fixed`; if it is
not really fixed, report it again with its ID. Raise an entry with status `rejected` again
only with a new argument, keeping its ID.
<content of ledger.md>

Rules:
- A finding is `blocking` only if it violates a named rubric criterion, gives a location, and
  the artifact would be wrong or unusable because of it. Style and taste are `minor`.
- Output contract, exactly. The first line is `VERDICT: APPROVED`, `VERDICT: REVISE` or
  `VERDICT: BLOCKED`. APPROVED means no blocking finding is open. REVISE means at least one
  blocking finding is open. BLOCKED means a decision only the human owner can make is needed.
  Then one line per finding and nothing else:
  <ID> | blocking or minor | criterion: <name> | <location> | <problem and suggested fix>
  <ID> is `new` for a new finding, or the ledger ID of the entry the finding repeats.
- No text before the VERDICT line, no code fence, no summary.
```

CLI author prompt:

```text
You are the author of the artifact at <target path>. Task: <content of task.md>

Rubric the reviewer applies:
<content of rubric.md>

<For the first author step of a task run: "Write the artifact at <target path>.">
<Otherwise: "Handle every finding with status `open` and severity `blocking` in this ledger:
fix it in the artifact, or reject it with a reason.">
<content of ledger.md>

Change only <target path>. End your reply with one line per open blocking finding:
<ID> | fixed
<ID> | rejected | <reason>
```

## 8. Stop report

Every stop after the preflight reports:

- the outcome: approved, handed over (blocked, cap reached, disputed rejection), contract
  violation, CLI failure (with the quoted stderr), or unchanged target;
- the artifact path, the ledger path `$RUN/ledger.md`, and the review number `R`;
- on approval, the minor findings; on hand-over, the open blocking findings;
- any files changed outside the target by a CLI author.

Keep `$RUN`. A stopped run cannot be resumed; calling Arena again on the same path starts a
new run on the current state.
