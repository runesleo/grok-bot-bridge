# Changelog

## [Unreleased]

### Added
- Ready-made Grok Bot template with the inbox routine built in: https://x.ai/bot/nnPi-WVku_162DIxfqZ3Z

## [0.1.0] - 2026-10-25

### Added
- `send`: post `{job_id, task}` to a Grok Bot webhook routine, at most once per job id; timeouts recorded as `UNKNOWN`, never retried.
- `harvest`: collect `BRIDGE_RESULT <job_id>` replies from the Grok Bot macOS app's local chat copies into `results/<job_id>.md`.
- `status`: latest ledger row for a job.
- Setup prompt (English and Chinese) that makes the Bot create its own webhook routine.
