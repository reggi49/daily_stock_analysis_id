#!/usr/bin/env python3
"""
AI code review script used by GitHub Actions PR Review workflow.
"""
import json
import os
import subprocess
import traceback


MAX_DIFF_LENGTH = 18000
REVIEW_PATHS = [
    '*.py',
    '*.md',
    'README.md',
    'AGENTS.md',
    'docs/**',
    '.github/PULL_REQUEST_TEMPLATE.md',
    'requirements.txt',
    '.github/requirements-ci.txt',
    'pyproject.toml',
    'setup.cfg',
    '.github/workflows/*.yml',
    '.github/scripts/*.py',
    'apps/dsa-web/**',
]


def run_git(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"⚠️ Git command failed: {' '.join(args)}")
        print(result.stderr.strip())
        return ''
    return result.stdout.strip()


def get_diff():
    """Get PR diff content for review-relevant files."""
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main')
    diff = run_git(['git', 'diff', f'origin/{base_ref}...HEAD', '--', *REVIEW_PATHS])
    truncated = len(diff) > MAX_DIFF_LENGTH
    return diff[:MAX_DIFF_LENGTH], truncated


def get_changed_files():
    """Get changed file list for review-relevant files."""
    base_ref = os.environ.get('GITHUB_BASE_REF', 'main')
    output = run_git(['git', 'diff', '--name-only', f'origin/{base_ref}...HEAD', '--', *REVIEW_PATHS])
    return output.split('\n') if output else []


def get_pr_context():
    """Read PR title/body from GitHub event payload when available."""
    event_path = os.environ.get('GITHUB_EVENT_PATH')
    if not event_path or not os.path.exists(event_path):
        return '', ''
    try:
        with open(event_path, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        pr = payload.get('pull_request', {})
        return (pr.get('title') or '').strip(), (pr.get('body') or '').strip()
    except Exception:
        return '', ''


def classify_files(files):
    py_files = [f for f in files if f.endswith('.py')]
    doc_files = [f for f in files if f.endswith('.md') or f.startswith('docs/') or f in ('README.md', 'AGENTS.md')]
    frontend_files = [f for f in files if f.startswith('apps/dsa-web/') or f.endswith(('.tsx', '.ts'))]
    ci_files = [f for f in files if f.startswith('.github/workflows/')]
    config_files = [
        f for f in files if f in ('requirements.txt', '.github/requirements-ci.txt', 'pyproject.toml', 'setup.cfg', '.github/PULL_REQUEST_TEMPLATE.md')
    ]
    return py_files, doc_files, frontend_files, ci_files, config_files


def _build_ci_context():
    """Build CI context section from environment variables set by the workflow."""
    auto_check_result = os.environ.get('CI_AUTO_CHECK_RESULT', '')
    syntax_ok = os.environ.get('CI_SYNTAX_OK', '')
    has_py = os.environ.get('CI_HAS_PY_CHANGES', 'false')

    if not auto_check_result:
        return """
## CI Check Status
> ⚠️ No CI check result obtained. Do not assume CI passed during review; verification-related judgments should be marked as "unable to confirm".
"""

    lines = ["\n## CI Check Status (from this PR's automated pipeline)"]
    lines.append(f"- Overall static check result: **{'✅ Passed' if auto_check_result == 'success' else '❌ Failed'}**")
    if has_py == 'true':
        lines.append(f"- Python syntax check (py_compile): **{'✅ Passed' if syntax_ok == 'true' else '❌ Failed' if syntax_ok == 'false' else '⏭️ Not executed'}**")
        lines.append("- Flake8 critical error check (E9/F63/F7/F82): **✅ Passed** (if it failed, the overall static check would have failed)")
    else:
        lines.append("- Python files: no changes, syntax check skipped")
    lines.append("")
    lines.append("> The above CI only covers syntax correctness (py_compile) and fatal lint errors (flake8 E9/F63/F7/F82). `./scripts/ci_gate.sh` **is not included in CI**: for Python backend changes, if the PR description does not state whether this gate was executed (or give a skip reason), it should be noted in the suggestions, but it is not a blocker. If syntax/flake8 passed, there is no need to repeat the corresponding local output.")
    lines.append("")
    return '\n'.join(lines)


def build_prompt(diff_content, files, truncated, pr_title, pr_body):
    """Build AI review prompt aligned with AGENTS.md requirements."""
    truncate_notice = ''
    if truncated:
        truncate_notice = "\n\n> ⚠️ Note: the diff is too long and has been truncated; please review based on the visible content and mark uncertain points.\n"

    py_files, doc_files, frontend_files, ci_files, config_files = classify_files(files)
    ci_context = _build_ci_context()
    return f"""You are the PR review assistant for this repository. Based on the changes and the PR description, perform a joint "code + docs + CI" review.

## PR Information
- Title: {pr_title or '(empty)'}
- Description:
{pr_body or '(empty)'}

## Modified File Statistics
- Python: {len(py_files)}
- Docs/Markdown: {len(doc_files)}
- Frontend (apps/dsa-web): {len(frontend_files)}
- CI Workflow: {len(ci_files)}
- Config/Template: {len(config_files)}

Modified file list:
{', '.join(files)}{truncate_notice}

## Code Changes (diff)
```diff
{diff_content}
```
{ci_context}
## Review Rules to Align With (from repo AGENTS.md)
1. Necessity: Is there a clear problem/business value, avoiding ineffective refactoring.
2. Traceability: Is there an associated Issue (Fixes/Refs); natural-language association (e.g. "related issue #xxx") is also acceptable, not rejected over formatting. If no Issue, is the motivation and acceptance criteria given.
3. Type: Does fix/feat/refactor/docs/chore/test match.
4. Description Completeness: Does it include background, scope, verification commands and results, compatibility risk, rollback plan. When judging whether verification is sufficient, you must refer to the "CI Check Status" section above: (a) if py_compile and flake8 passed, the PR description may reference CI results without pasting the corresponding local output; (b) `./scripts/ci_gate.sh` is not in CI coverage, for Python backend changes check whether the PR description states whether this gate was executed, if not it should be listed as a suggestion; (c) if no CI result is provided, do not assume CI passed, verification sufficiency should be marked as "unable to confirm".
5. Merge Readiness: Give Ready / Not Ready, and list blockers.
6. If user-visible capabilities are involved, check whether README.md and docs/CHANGELOG.md are in sync.

## Blocker vs Suggestion Criteria
Only the following can be judged Not Ready (blockers/must-fix):
- Code has correctness or security issues (logic errors, swallowed exceptions, security vulnerabilities, etc.)
- CI check not passed
- PR description has a substantive contradiction with the actual changes
- Missing rollback plan

The following only go into suggestions and do not affect the merge decision:
- Issue association format non-standard
- Syntax/flake8 verification evidence missing but the "CI Check Status" above shows py_compile and flake8 both passed
- PR description for Python backend changes does not state whether `./scripts/ci_gate.sh` was executed or give a skip reason
- Non-critical wording or formatting issues in description
- Comment language style, unrelated lockfile changes, etc.

## Review Output Requirements
- Use English.
- First give the "Conclusion": `Ready to Merge` or `Not Ready`.
- Then give structured results:
  - Necessity: pass/fail + reason
  - Traceability: pass/fail + evidence
  - Type: suggested type
  - Description completeness: complete/incomplete (missing items)
  - Risk level: low/medium/high + key risk
  - Must-fix items (max 5, only blocker conditions, by priority)
  - Suggestions (max 5)
- Must-fix items only include the blocker-condition issues above; formatting, traceability, verification-evidence and other non-blocker issues go into suggestions.
- For identified issues, locate to the file path as much as possible and explain the impact.
- If information is insufficient, explicitly write "unable to confirm based on current diff/PR description".
"""


def review_with_gemini(prompt):
    """Run review with Gemini API."""
    api_key = os.environ.get('GEMINI_API_KEY')
    model = os.environ.get('GEMINI_MODEL') or os.environ.get('GEMINI_MODEL_FALLBACK') or 'gemini-2.5-flash'

    if not api_key:
        print("❌ Gemini API Key not configured (check GitHub Secrets: GEMINI_API_KEY)")
        return None

    print(f"🤖 Using model: {model}")

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=prompt
        )
        print(f"✅ Gemini ({model}) review succeeded")
        return response.text
    except ImportError as e:
        print(f"❌ Gemini dependency not installed: {e}")
        print("   Please ensure google-genai is installed: pip install google-genai")
        return None
    except Exception as e:
        print(f"❌ Gemini review failed: {e}")
        traceback.print_exc()
        return None


def review_with_openai(prompt):
    """Run review with OpenAI-compatible API as fallback."""
    api_key = os.environ.get('OPENAI_API_KEY')
    base_url = os.environ.get('OPENAI_BASE_URL', 'https://api.openai.com/v1')
    model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')

    if not api_key:
        print("❌ OpenAI API Key not configured (check GitHub Secrets: OPENAI_API_KEY)")
        return None

    print(f"🌐 Base URL: {base_url}")
    print(f"🤖 Using model: {model}")

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.3
        )
        print(f"✅ OpenAI-compatible interface ({model}) review succeeded")
        return response.choices[0].message.content
    except ImportError as e:
        print(f"❌ OpenAI dependency not installed: {e}")
        print("   Please ensure openai is installed: pip install openai")
        return None
    except Exception as e:
        print(f"❌ OpenAI-compatible interface review failed: {e}")
        traceback.print_exc()
        return None


def ai_review(diff_content, files, truncated):
    """Run AI review: Gemini first, then OpenAI fallback."""
    pr_title, pr_body = get_pr_context()
    prompt = build_prompt(diff_content, files, truncated, pr_title, pr_body)

    result = review_with_gemini(prompt)
    if result:
        return result

    print("Trying OpenAI-compatible interface...")
    result = review_with_openai(prompt)
    if result:
        return result

    return None


def main():
    diff, truncated = get_diff()
    files = get_changed_files()

    if not diff or not files:
        print("No reviewable code/docs/config changes, skipping AI review")
        summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
        if summary_file:
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write("## 🤖 AI Code Review\n\n✅ No reviewable changes\n")
        return

    print(f"Reviewing files: {files}")
    if truncated:
        print(f"⚠️ Diff content truncated to {MAX_DIFF_LENGTH} characters")

    review = ai_review(diff, files, truncated)

    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')

    strict_mode = os.environ.get('AI_REVIEW_STRICT', 'false').lower() == 'true'

    if review:
        if summary_file:
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write(f"## 🤖 AI Code Review\n\n{review}\n")

        with open('ai_review_result.txt', 'w', encoding='utf-8') as f:
            f.write(review)

        print("AI review complete")
    else:
        print("⚠️ All AI interfaces are unavailable")
        if summary_file:
            with open(summary_file, 'a', encoding='utf-8') as f:
                f.write("## 🤖 AI Code Review\n\n⚠️ AI interface unavailable, please check configuration\n")
        if strict_mode:
            raise SystemExit("AI_REVIEW_STRICT=true and no AI review result is available")


if __name__ == '__main__':
    main()
