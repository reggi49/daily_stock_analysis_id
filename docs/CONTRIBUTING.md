# Contributing Guide

Thank you for your interest in this project! Contributions of any kind are welcome.

## 🐛 Report Bugs

1. First search [Issues](https://github.com/ZhuLinsen/daily_stock_analysis/issues) to confirm the issue hasn't been reported
2. Create a new Issue using the Bug Report template
3. Provide detailed reproduction steps and environment information

## 💡 Feature Suggestions

1. First search Issues to confirm the suggestion hasn't been made
2. Create a new Issue using the Feature Request template
3. Describe your use case and expected functionality in detail

## 🔧 Submitting Code

### Development Environment

```bash
# Clone the repository
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
cd daily_stock_analysis

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
```

### Submission Process

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'feat: add some feature'`
4. Push the branch: `git push origin feature/your-feature`
5. Create a Pull Request

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: new feature
fix: bug fix
docs: documentation update
style: code format (no functional change)
refactor: refactoring
perf: performance optimization
test: test related
chore: build/tool related
```

Example:
```
feat: add DingTalk bot support
fix: fix 429 rate limit retry logic
docs: update README deployment instructions
```

### Code Standards

- Python code follows PEP 8
- Functions and classes need docstrings
- Important logic needs comments
- New features need to update related documentation

### CI Automated Checks

After submitting a PR, CI will automatically run the following checks:

| Check Item | Description | Must Pass |
|--------|------|:--------:|
| backend-gate | `scripts/ci_gate.sh` (py_compile + flake8 critical errors + local core scripts + offline pytest) | ✅ |
| docker-build | Docker image build and critical module import smoke test | ✅ |
| web-gate | Runs `npm run lint` + `npm run build` when frontend files change | ✅ (when triggered) |
| network-smoke | Scheduled/manual `pytest -m network` + `scripts/test.sh quick` (non-blocking) | ❌ (observational) |

**Running checks locally:**

```bash
# Backend gate (recommended)
pip install -r requirements.txt
pip install flake8 pytest
./scripts/ci_gate.sh

# Frontend gate (if apps/dsa-web was modified)
cd apps/dsa-web
npm ci
npm run lint
npm run build
```

## 📋 Priority Contribution Areas

Check the [Roadmap](README.md#-roadmap) for current feature needs:

- 🔔 New notification channels (DingTalk, Feishu, Telegram)
- 🤖 New AI model support (GPT-4, Claude)
- 📊 New data source integration
- 🐛 Bug fixes and performance optimization
- 📖 Documentation improvement and translation

## ❓ Questions

If you have any questions, feel free to:
- Create an Issue to discuss
- Check existing Issues and Discussions

Thank you again for your contribution! 🎉
