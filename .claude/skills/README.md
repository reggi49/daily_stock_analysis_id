# Repository Claude Skills

This directory stores warehouse-level collaboration skills，Belongs to the repository assets。

- The true source of rules：Warehouse root directory `AGENTS.md`
- Compatible entrance：root directory `CLAUDE.md`（should point to `AGENTS.md` soft link）
- in this directory skill Need and `AGENTS.md` Be consistent
- `.claude/reviews/` Belongs to local analysis product，Not as the true source of rules

If compatibility with other systems is required in the future agent Directory（Such as `.agents/skills/` or `.github/skills/`），A single source of truth should first be identified，Then synchronize through script or mirror，Instead of manually maintaining multiple copies of synonymous content for a long time。
