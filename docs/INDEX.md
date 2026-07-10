# Documentation Hub

This is the project documentation entry point. README covers project overview and quick start; more complete configuration, deployment, feature details, and troubleshooting are accessible from here.

## Choose by Scenario

| I want to | Start with | Then see |
| --- | --- | --- |
| Quickly understand what the project does | [README](../README.md) | [Full Configuration & Deployment Guide](full-guide.md) |
| Run the project for the first time | [Beginner Client Setup](beginner-client-setup.md) | [Full Configuration & Deployment Guide](full-guide.md) |
| Configure LLM channels | [LLM Configuration Guide](LLM_CONFIG_GUIDE.md) | [LLM Provider Configuration Guide](llm-providers.md) |
| Configure push notifications | [Notification Capabilities Baseline](notifications.md) | [Full Configuration & Deployment Guide](full-guide.md) |
| Deploy to a server or cloud platform | [Deployment Guide](DEPLOY.md) | [Cloud WebUI Deployment](deploy-webui-cloud.md), [Zeabur Deployment](docker/zeabur-deployment.md) |
| Use Bot / IM integration | [Bot Commands & Integration](bot-command.md) | [Bot Platform Configuration](bot/) |
| Troubleshoot runtime issues | [FAQ](FAQ.md) | [Changelog](CHANGELOG.md) |
| Handle data source failures or degradation | [Data Source Stability & Fault Handling](data-source-stability.md) | [FAQ](FAQ.md) |
| Contribute or submit a PR | [Contributing Guide](CONTRIBUTING.md) | [API Spec](architecture/api_spec.json) |

## Quick Start

| Document | Content |
| --- | --- |
| [README](../README.md) | Project overview, core capabilities, quick start, notification previews |
| [Beginner Client Setup](beginner-client-setup.md) | Client download for non-developers, Anspire Open / AIHubMix model configuration, news source setup, and common issues |
| [Full Configuration & Deployment Guide](full-guide.md) | Environment setup, run methods, configuration details, deployment paths, and common issues |
| [FAQ](FAQ.md) | Common configuration, model, notification, deployment, and runtime issues |
| [Data Source Stability & Fault Handling](data-source-stability.md) | Use cases, fallback chains, and recommended configuration for Tushare, TickFlow, AkShare, Efinance, YFinance, Longbridge, and other integrated sources |
| [Changelog](CHANGELOG.md) | Version changes, capability adjustments, and migration notes |

## Configuration

| Document | Content |
| --- | --- |
| [LLM Configuration Guide](LLM_CONFIG_GUIDE.md) | LLM channels, three-tier configuration, Web settings page, and common model configuration |
| [LLM Provider Configuration Guide](llm-providers.md) | Provider presets, Actions mapping, error classification, and diagnostic recommendations |
| [LiteLLM YAML Examples](examples/litellm_config.example.yaml) | LiteLLM multi-channel configuration examples |
| [Notification Capabilities Baseline](notifications.md) | WeChat Work, Feishu, Telegram, Discord, Slack, email, and other notification channel configuration |
| [Tushare Stock List Guide](TUSHARE_STOCK_LIST_GUIDE.md) | Tushare stock list configuration and usage instructions |

## Topical Guides

| Document | Content |
| --- | --- |
| [Bot Commands & Integration](bot-command.md) | Bot commands, webhooks, platform integration, and callback instructions |
| [Bot Platform Configuration](bot/) | Feishu, DingTalk, Discord, and other bot configuration screenshots and supplementary notes |
| [Real-time Alert Center](alerts.md) | EventMonitor baseline, Web rule management, notification results, cooldown status, and Phase boundaries |
| [DecisionSignal Topic](decision-signals.md) | AI recommendation pool field semantics, API, Web display, alert/notification/portfolio risk linkage, post-hoc evaluation, sanitization, migration & rollback |
| [News / Intelligence Sources](intelligence-sources.md) | RSS/Atom compliant news source configuration, testing, fetching, deduplication, storage, querying, and security boundaries |
| [Analysis Context Pack Contract, Runtime Consumption & Visibility](analysis-context-pack.md) | AnalysisContextPack v1 scope, field quality status, P1/P2 internal contracts, P3 Prompt summary consumption, P4 history/API/Web low-sensitivity visibility, P5 data quality scoring, P6 migration rollback & source anchoring; full guide supplement #1386 phase-aware analysis, migration & rollback entry points |
| [Image Recognition Prompt](image-extract-prompt.md) | Stock information extraction prompt and usage boundaries |
| [OpenClaw Skill Integration](openclaw-skill-integration.md) | OpenClaw / Skill external integration instructions |

## Deployment & Packaging

| Document | Content |
| --- | --- |
| [Deployment Guide](DEPLOY.md) | Server deployment, Docker, systemd, Supervisor, and other deployment methods |
| [Cloud WebUI Deployment](deploy-webui-cloud.md) | Cloud server WebUI deployment instructions |
| [Zeabur Deployment](docker/zeabur-deployment.md) | Zeabur platform deployment instructions |
| [Desktop Packaging Guide](desktop-package.md) | Electron desktop app and Web build artifact packaging instructions |

## Reference & Development

| Document | Content |
| --- | --- |
| [API Spec](architecture/api_spec.json) | FastAPI OpenAPI specification artifact |
| [Contributing Guide](CONTRIBUTING.md) | Issues, PRs, testing, documentation sync, and collaboration requirements |

## Multi-language

| Document | Content |
| --- | --- |
| [English Documentation Index](INDEX_EN.md) | English documentation index |
| [English README](README_EN.md) | English project overview and quick start |
| [Traditional Chinese README](README_CHT.md) | Traditional Chinese project overview and quick start |
