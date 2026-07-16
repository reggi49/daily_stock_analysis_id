# Fix Issue

Based on issue Analyze results and implement repairs，And complete the verification according to the warehouse rules、Risk and rollback instructions。

**Repository**: https://github.com/ZhuLinsen/daily_stock_analysis

## Usage

```text
/fix-issue <issue_number>
```

## Prerequisites

Complete first `/analyze-issue <issue_number>`，Make sure the problem is established and the boundaries are clear。

## Instructions

### Step 1: Confirm analysis baseline

Check `.claude/reviews/issues/issue-<number>.md` exists；if does not exist，Make up for it first issue Analyze or complete the minimum analysis conclusion in this repair。

### Step 2: Sync the latest code baseline and choose a secure way to work

Start repairing or prepare to create / update PR before，Press first `AGENTS.md` Recruit：

```bash
git status --short
git fetch --all --prune
# Only if the workspace is clean and the current branch is available fast-forward executed when：
git pull --ff-only
```

- By default, minimal relevant changes are made based on the current working tree.
- Only clean the work area、The current branch is available fast-forward of the upstream，only then execute and accept `git pull --ff-only` the result
- If there are local changes、Conflict status、Risk files not tracked、No upstream branch or unable to fast-forward，Don't execute `stash`、`reset`、Force branch cutting or overwrite local state；Record local first HEAD、The remote baseline used and the reason why the local working tree cannot be updated
- If you want to create it later / update PR，First explain the difference between the current branch and the target baseline；Request user confirmation if necessary rebase、merge Or continue to advance based on the current branch
- Do not switch branches by default or overwrite the user's current working status
- If the user explicitly requests to create a branch，Then perform the minimum necessary branch operations

### Step 3: Implement a fix

- According to issue Conclusion and positioning related documents
- Prioritize reuse of existing modules、Configuration entry、Scripts and tests
- Keep default behavior backwards compatible，avoid destruction fallback / fail-open
- If the fix involves user-visible behavior、Configuration semantics、CLI/API、deploy、Notification、Report structure，To synchronize and update related documents、`docs/CHANGELOG.md`、`.env.example`
- towards `docs/CHANGELOG.md` When writing an entry，in `[Unreleased]` Add a line to a paragraph，The format is `- [Type] Description`，Among them `[Type]` from `[new features]/[Improve]/[Repair]/[Documentation]/[test]/[chore]` Press the middle button to select the content of this change.；Only fix bug Use only when `[Repair]`；**Don't**in `[Unreleased]` Add within `### Category title`
- `README.md` Only carries project positioning、core competencies、quick start、main entrance、Sponsor/Home page-level information such as cooperation；Do not update unless necessary README，Avoid continued expansion
- More granular module behavior、Page interaction、Thematic configuration、Troubleshooting instructions、field contract、Implement semantics and boundary conditions，Prioritize update correspondence `docs/*.md`

### Step 4: Verify by modified surface

press `AGENTS.md` The validation matrix performs the closest check：

- Backend first：`./scripts/ci_gate.sh`
- Minimum backend requirements：`python -m py_compile <changed_python_files>`
- front end：`cd apps/dsa-web && npm ci && npm run lint && npm run build`
- Desktop：Build first Web，Build the desktop again

If complete verification cannot be completed，Gaps must be recorded、Reasons and potential risks。

### Step 5: update issue Analyze documents

in `.claude/reviews/issues/issue-<number>.md` middle supplement：

```markdown
## Fix Implementation

**Date**: YYYY-MM-DD

### Changes Made

- Documents and changes：

### Validation

- Executed：
- Not executed：

### Risks

- Risk point：

### Rollback

- Rollback mode：
```

### Step 6: Follow-up actions requiring confirmation

Created as requested by the user PR、generate PR Title or organize PR Description，PR title It is recommended to follow `AGENTS.md`：

- Use `<Type>: <Modify content>` Format，For example `fix: Repair the loss of market analysis history records`
- Type takes precedence `fix`/`feat`/`refactor`/`docs`/`chore`/`test`/`ci`
- The title only describes the actual changes，It is recommended not to add `[codex]`、`codex`、`autocode`、`copilot` or other tools/agent source prefix
- This convention is only for collaborative consistency，should not be considered alone process blocker

Only after explicit confirmation by the user，before execution：

- Create a branch
- `git commit`
- `git push`
- create PR
- in issue Reply or close issue

## Allowed Auto-Actions (No Confirmation Needed)

- Read and analyze code
- execute `git fetch --all --prune`，and keep the work area clean and accessible fast-forward executed when `git pull --ff-only`
- Apply minimal fixes directly related to the current task
- Run non-destructive local verification
- Update local issue Analyze documents

## Actions Requiring Confirmation

1. Switch or create a branch
2. `git commit`
3. `git push`
4. create PR
5. reply or close issue
