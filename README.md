# Grok Bot Bridge

**Let Claude Code, ChatGPT or any script hand tasks to your Grok Bots — each task sent once, every answer collected back into a file with one command.**

![license](https://img.shields.io/badge/license-MIT-blue) ![python](https://img.shields.io/badge/python-3.9%2B-blue) ![deps](https://img.shields.io/badge/dependencies-none-green)

[中文说明](README.zh.md)

## What you get

- **A task inbox per Bot.** One short prompt makes the Bot build its own webhook routine; no clicking through settings.
- **Send once.** Every task carries a job id and a local ledger records it. The same id is never sent twice; if a send times out, it is marked `UNKNOWN` and never retried blindly. The Bot also checks the id and answers `BRIDGE_DUP` for a repeat.
- **Answers come back with one command.** The Bot replies with `BRIDGE_RESULT <job_id>` on the first line; `harvest` saves each reply to `results/<job_id>.md` and marks the job `REPLIED`.
- **One file, no dependencies.** Python standard library only.

## Why

Driving a chat window from a program is fragile: when it cannot read the reply, it assumes the message never went out and sends it again. One of my tasks was resent 17 times in 5 hours — 15 of those had already arrived. A webhook plus a job id turns "hope it got there" into a receipt.

## How it works

```text
your agent ──send(bot, job_id, task)──▶ Grok Bot webhook routine
     ▲                                        │ does the task
     │                                        ▼
results/<job_id>.md ◀──harvest── "BRIDGE_RESULT <job_id>\n…" in the Bot's chat
```

## Setup

1. **Let the Bot build its inbox.** Send [setup-prompt.md](setup-prompt.md) in the Bot's chat.
2. **Copy the webhook.** In the Grok Bot desktop app, open the Bot's details → Routines, **right-click** the "Task Inbox" row → Webhook, and copy the Webhook URL and key into `~/.grok-bridge/bots.env` (pick any name, one pair per Bot):

   ```
   BRIDGE_URL_RESEARCH=<Webhook URL>
   BRIDGE_KEY_RESEARCH=<Webhook key>
   ```

   ```bash
   mkdir -p ~/.grok-bridge && touch ~/.grok-bridge/bots.env && chmod 600 ~/.grok-bridge/bots.env
   ```

   Then open the file and paste the two lines.

3. **Get the script.**

   ```bash
   git clone https://github.com/runesleo/grok-bot-bridge.git
   ```

   ```bash
   cd grok-bot-bridge
   ```

For agents: [install.md](install.md) is written for Claude Code / Codex to follow.

## Quick start

```bash
python3 grok_bridge.py send research job-001 "Reply with one line: the current time in UTC."
```

```bash
python3 grok_bridge.py harvest
```

```bash
python3 grok_bridge.py status job-001
```

In Claude Code: put the folder in your project and tell it "send Grok tasks with `grok_bridge.py send`, job id `<task>-<time>`; run `harvest` after a while and read `results/`."

## Requirements

- Python 3.9+.
- Grok Bot with routines and webhook triggers.
- `harvest` needs the **Grok Bot macOS desktop app** on the same Mac: it reads the app's local chat copies, read-only.

**Privacy:** the webhook key is the key to that inbox — keep it out of chats, screenshots and public repos. Config, ledger and results all live in `~/.grok-bridge/` (set `GROK_BRIDGE_HOME` to move all three); the script refuses non-`https://` webhook URLs; nothing is sent anywhere except the webhook you configured.

## Verified

2026-10-25, three Bots on one account: short tasks answered in about 1 minute; a task that analysed a week of posts answered in 12 minutes; a repeated job id was blocked locally, and the Bot answered `BRIDGE_DUP` when a repeat reached it. `python3 -m pytest -q test_grok_bridge.py` runs offline with fake data and sends nothing.

## Known limitations (v0.1)

- `harvest` relies on the desktop app's local storage, which is not a public API; an app update may need a matching fix. `send` uses the official webhook and is not affected.
- macOS only for `harvest`. On other systems, read the Bot's reply in the app.
- The "do only the task, don't post / like / touch wallets" line is an instruction to the Bot, not a hard limit. Don't give a task-inbox Bot posting, wallet or account tools, and treat the key like a password.
- `harvest` matches by job id across all local chats; use unique ids (e.g. `<task>-<timestamp>`).
- The Bot must keep the `BRIDGE_RESULT <job_id>` first line; if it doesn't, the reply is not collected.

## Roadmap

- Wait-for-reply mode (`send --wait`) with a timeout.
- A `/send-to-grok` skill file for Claude Code.

## About the author

*Leo ([@runes_leo](https://x.com/runes_leo)) — AI × Crypto independent builder. Trading on [Polymarket](https://polymarket.com/?via=runes-leo&r=runesleo&utm_source=github&utm_content=grok-bot-bridge), building data and content pipelines with Claude Code and Codex.*

*[leolabs.me](https://leolabs.me) — writing · community · open-source tools · indie projects · all platforms.*

*[X Subscription](https://x.com/runes_leo/creator-subscriptions/subscribe) — paid content weekly, or just buy me a coffee 😁*

*Learn in public, Build in public.*

## License

MIT
