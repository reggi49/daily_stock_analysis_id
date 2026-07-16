# Analyze PR

analysis GitHub Pull Request，Assess the necessity、description completeness、verification evidence、Main risks and whether it can be directly integrated。

**Repository**: https://github.com/ZhuLinsen/daily_stock_analysis/pulls

## Usage

```text
/analyze-pr <pr_number>
```

## Instructions

Use concise Chinese when analyzing，Prioritize the warehouse root directory `AGENTS.md` and `.github/PULL_REQUEST_TEMPLATE.md`。

### Step 1: Synchronize the latest code baseline

analysis PR The remote status must be refreshed before，And try to push local security to the latest baseline：

```bash
git status --short
git fetch --all --prune
# Only if the workspace is clean and the current branch is available fast-forward executed when：
git pull --ff-only
```

- Only clean the work area、The current branch is available fast-forward of the upstream，only then execute and accept `git pull --ff-only` the result。
- If there are local changes、Conflict status、Risk files not tracked、No upstream branch or unable to fast-forward，Don't execute `stash`、`reset`、Force branch cutting or overwrite local state；Used instead fetch of `origin/main`、PR head or GitHub diff do analysis。
- In the output document `Validation Evidence` Record synchronization results in：local HEAD、remote baseline used，and the reason why the local working tree is not updated（If any）。

### Step 2: pull PR Basic information

```bash
gh pr view <pr_number> --repo ZhuLinsen/daily_stock_analysis
gh pr view <pr_number> --repo ZhuLinsen/daily_stock_analysis --comments
gh pr checks <pr_number> --repo ZhuLinsen/daily_stock_analysis
gh pr diff <pr_number> --repo ZhuLinsen/daily_stock_analysis
```

If there is any failure CI，Check the failure log first，Instead of immediately re-running all checks locally：

```bash
gh run view <run_id> --log-failed
```

### Step 3: Check title and description completeness

Check first PR title Does it comply with `AGENTS.md` non-blocking recommendations：

- The format should be `<Type>: <Modify content>`，For example `fix: Repair the loss of market analysis history records`
- The type priority is `fix`/`feat`/`refactor`/`docs`/`chore`/`test`/`ci`
- should not contain `[codex]`、`codex`、`autocode`、`copilot` or other tools/agent source prefix
- The title should describe the actual change；If the title matches diff Does not match，noted in description completeness，but should not be used alone review process blocker。

control `.github/PULL_REQUEST_TEMPLATE.md`，Confirm whether it is covered：

- `PR Type`
- `Background And Problem`
- `Scope Of Change`
- `Issue Link`
- `Verification Commands And Results`
- `Visual Evidence`（only if PR Modify report format、Report rendering effects or Web UI Interface requires screenshots or alternative visual evidence）
- `Compatibility And Risk`
- `Rollback Plan`

If PR Involves third-party models / API Compatible semantics、Request parameter fixed value、OpenAI-compatible routing、YAML alias、fallback Behavior or runtime configuration saving / clean up / Migration logic，Also check to see if it is clearly written in the description.：

- Official source link or announcement
- Current lock dependencies / Runtime compatibility range（For example LiteLLM version window）
- Verified call link coverage
- Will old configurations be silently overwritten?、Clear、Migrate or stay the same
- minimal rollback path（usually revert Ben PR）

If PR Modify report format、Report rendering effects or Web UI interface，Also check `Visual Evidence` Is an impact report attached? / Page screenshot；When it comes to differences before and after, check the before and after comparison first.。If you cannot take a screenshot，Description should include reasons and alternative visual evidence。

### Step 4: priority use CI / Diff evidence

- first based on `gh pr checks`、PR diff、Existing test and workflow log judgment issues
- only if CI Changes not covered、CI The results are not sufficient to characterize the problem、or when critical regression risks need to be verified，Add local minimum verification
- Don't default to switching the current branch or execution `gh pr checkout`

If local verification is required，Select the closest inspection by modified face，For example：

- backend：`./scripts/ci_gate.sh` or `python -m py_compile <changed_python_files>`
- front end：`cd apps/dsa-web && npm ci && npm run lint && npm run build`
- Desktop：Build first Web，Rebuild Electron

### Step 5: Assess correctness and risk

Key inspections：

- Has a clear problem been solved?，and no entrainment of irrelevant changes
- whether to destroy API / Schema / Web / Desktop Compatibility
- whether to destroy fallback、Downgrade path、Notification link or publishing process
- Are there obvious logical errors?、Abnormal engulfment、security issues、Configuration semantic changes do not synchronize documents

### Step 6: Generate review documents

save to `.claude/reviews/prs/pr-<number>.md`

## Output Document Format

```markdown
# PR #<number> Analysis

**Date**: YYYY-MM-DD
**Status**: Pending Review

## Findings

- [Severity level] file:line - Problem description

## Summary

- Necessity：
- Is there any correspondence? issue：
- PR Type：
- PR title：
- description integrity：
- Verification status：
- Main risks：
- Can it be directly integrated?：

## Validation Evidence

- Code synchronization baseline：
- CI Conclusion：
- Local supplementary verification（If any）：

## Compatibility And Risk

- API / Web / Desktop：
- Configuration / Docker / GitHub Actions：
- fallback / Notification / Report structure：
- third party dependencies / Official binding source：
- runtime compatibility window / Link covered：
- Risks of old configuration migration or silent rewriting：

## Draft Review Comment

<Suggested comment content>
```

## Allowed Auto-Actions (No Confirmation Needed)

- pull PR metadata、diff、comments and CI Status
- execute `git fetch --all --prune`，and keep the work area clean and accessible fast-forward executed when `git pull --ff-only`
- Read the relevant code、Template、Workflow and documentation
- Perform minimal local validation when necessary
- Generate review documents

## Actions Requiring Confirmation

Before performing the following actions，Ask the user first：

1. Post a comment
2. Approve PR
3. Request changes
4. Merge PR
5. close PR
