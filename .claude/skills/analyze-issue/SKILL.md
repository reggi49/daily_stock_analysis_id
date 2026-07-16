# Analyze Issue

analysis GitHub Issue，judge its authenticity、priority、Warehouse responsibility boundaries and recommended actions。

**Repository**: https://github.com/ZhuLinsen/daily_stock_analysis/issues

## Usage

```text
/analyze-issue <issue_number>
```

## Instructions

Use concise Chinese when analyzing，Prioritize the warehouse root directory `AGENTS.md`。

### Step 1: Synchronize the latest code baseline

analysis issue The remote status must be refreshed before，And try to push local security to the latest baseline：

```bash
git status --short
git fetch --all --prune
# Only if the workspace is clean and the current branch is available fast-forward executed when：
git pull --ff-only
```

- Only clean the work area、The current branch is available fast-forward of the upstream，only then execute and accept `git pull --ff-only` the result。
- If there are local changes、Conflict status、Risk files not tracked、No upstream branch or unable to fast-forward，Don't execute `stash`、`reset`、Force branch cutting or overwrite local state；Used instead fetch of `origin/main` or related remote refs do analysis。
- In the output document `Evidence` Record synchronization results in：local HEAD、remote baseline used，and the reason why the local working tree is not updated（If any）。

### Step 2: pull Issue information

```bash
gh issue view <issue_number> --repo ZhuLinsen/daily_stock_analysis
gh issue view <issue_number> --repo ZhuLinsen/daily_stock_analysis --comments
```

If so bug，Priority check issue Is the following information provided in the template?：

- Has it been synced to the latest version?
- commit hash / version baseline
- Operating environment and reproduction steps
- Log or error message

### Step 3: answer 4 core question

1. Is the version clear?
2. Is the problem real and verifiable?
3. Does it fall within the warehouse responsibility boundary?
4. Is it worth dealing with immediately?

### Step 4: Conduct evidence inspection based on the current situation of the warehouse

- Read the relevant code、Configuration、test、script、Workflow and documentation
- If the question involves API、data source fallback、Report generation、Notification sent、Certification、Desktop、Release process，Clearly state the impact
- Judgment is actual bug、Environment configuration issues、Usage issues、Or is it an external dependency issue?
- If suspected it has been repaired，Check the current code instead of just looking issue Description

### Step 5: form a conclusion

Give at least the following fields：

- `version baseline`：Latest / Not up to date / Not provided
- `Is it reasonable?`：Yes/No + Reason
- `whether it is issue`：Yes/No + Reason
- `Is it easy to solve`：Yes/No + Difficulty
- `Conclusion`：`established / Partially established / Not established`
- `Classification`：`bug / feature / docs / question / external`
- `priority`：`P0 / P1 / P2 / P3`
- `difficulty`：`easy / medium / hard`
- `Recommended action`：`Fix now / Scheduled fixes / Documentation clarification / close`

### Step 6: Generate analysis documents

save to `.claude/reviews/issues/issue-<number>.md`

## Output Document Format

```markdown
# Issue #<number> Analysis

**Date**: YYYY-MM-DD
**Status**: Pending Review

## Summary

- version baseline：
- Is it reasonable?：
- whether it is issue：
- Is it easy to solve：
- Conclusion：
- Classification：
- priority：
- difficulty：
- Recommended action：

## Evidence

- Code synchronization baseline：
- key issue information：
- key code/script/Workflow evidence：

## Impact Scope

- Affected modules：
- Affected run paths（local / Docker / GitHub Actions / API / Web / Desktop）：

## Root Cause / Main Reasoning

<Root cause or main basis for judgment>

## Proposed Handling

<Suggested fix、clarify or close>

If it is recommended to create later PR，given PR title It is recommended to comply with `AGENTS.md`：Use `<Type>: <Modify content>`，Do not add `[codex]`、`codex`、`autocode`、`copilot` or other tools/agent source prefix；This convention is only used for collaborative consistency reminders，should not be used alone review process blocker。

## Risks And Rollback

- Risk point：
- If repaired，Rollback mode：

## Draft Reply

<Suggested reply content>
```

## Allowed Auto-Actions (No Confirmation Needed)

- pull issue Details and comments
- execute `git fetch --all --prune`，and keep the work area clean and accessible fast-forward executed when `git pull --ff-only`
- Read the relevant code、Configuration、script、Workflow and documentation
- Generate analysis documents

## Actions Requiring Confirmation

Before performing the following actions，Ask the user first：

1. Add or edit tags
2. in issue Leave a comment
3. close issue
4. Start repair issue
