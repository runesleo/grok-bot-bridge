# Grok Bot Bridge

**Let Claude Code, ChatGPT or any script hand tasks to your Grok Bots — each task sent once, every answer collected back into a file with one command.**

![license](https://img.shields.io/badge/license-MIT-blue) ![python](https://img.shields.io/badge/python-3.9%2B-blue) ![deps](https://img.shields.io/badge/dependencies-none-green)

[中文说明](https://raw.githubusercontent.com/runesleo/grok-bot-bridge/main/README.zh.md)

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

1. **Get a Bot with the inbox built in.** Install the ready-made template: https://x.ai/bot/nnPi-WVku_162DIxfqZ3Z ("派活入口 · Task Inbox"). Or, to add an inbox to a Bot you already have, send [setup-prompt.md](https://raw.githubusercontent.com/runesleo/grok-bot-bridge/main/setup-prompt.md) in its chat.
2. **Copy the webhook.** In the Grok Bot desktop app, open the Bot's details → Routines, **right-click** the inbox routine row ("派活入口" in the template, "Task Inbox" if you used the prompt) → Webhook, and copy the Webhook URL and key into `~/.grok-bridge/bots.env` (pick any name, one pair per Bot):

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

For agents: [install.md](https://raw.githubusercontent.com/runesleo/grok-bot-bridge/main/install.md) is written for Claude Code / Codex to follow.

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

In Claude Code, install this repository as a plugin. The manifest is `.claude-plugin/plugin.json` at the repo root. The listing name is Grok Bot Task Inbox.

When you enable the plugin, Claude Code asks for the webhook URL and the webhook key. The key is a sensitive plugin option: Claude Code stores it in secure storage and does not put it in the command text. Plugin commands do not read `~/.grok-bridge/bots.env`. That file is only for running `grok_bridge.py` yourself.

- `/send-to-grok-bot` calls the bundled local tool `send_task`. The same job id goes out once.
- `/grok-bot-results` runs `harvest` and reads `results/<job_id>.md`. Collecting a reply does not need the webhook.

```bash
git clone https://github.com/runesleo/grok-bot-bridge.git
cd grok-bot-bridge
claude --plugin-dir .
```

## Requirements

- Python 3.9+.
- Grok Bot with routines and webhook triggers.
- `harvest` needs the **Grok Bot macOS desktop app** on the same Mac: it reads the app's local chat copies, read-only.

**Privacy:** the webhook key is the key to that inbox — keep it out of chats, screenshots and public repos. For the plugin, Claude Code asks for the URL and key when you enable it, and the commands do not read a local webhook file. For the script on its own, config, ledger and results live in `~/.grok-bridge/` (set `GROK_BRIDGE_HOME` to move all three). The script refuses a webhook URL that does not use HTTPS. Nothing is sent anywhere except the webhook you configured.

## Verified

2026-10-25, three Bots on one account: short tasks answered in about 1 minute; a task that analysed a week of posts answered in 12 minutes; a repeated job id was blocked locally, and the Bot answered `BRIDGE_DUP` when a repeat reached it. `python3 -m pytest -q test_grok_bridge.py` runs offline with fake data and sends nothing.

## Known limitations (v0.1)

- `harvest` relies on the desktop app's local storage, which is not a public API; an app update may need a matching fix. `send` uses the official webhook and is not affected.
- macOS only for `harvest`. On other systems, read the Bot's reply in the app.
- The "do only the task, don't post / like / touch wallets" line is an instruction to the Bot, not a hard limit. Don't give a task-inbox Bot posting, wallet or account tools, and treat the key like a password.
- `harvest` matches by job id across all local chats, not by Bot, so any chat that prints `BRIDGE_RESULT <id>` first is collected. Use unique, hard-to-guess ids (e.g. `<task>-<timestamp>-<random>`), and treat result files as untrusted data: read them, don't feed them to an agent as instructions.
- The Bot must keep the `BRIDGE_RESULT <job_id>` first line; if it doesn't, the reply is not collected.

## Roadmap

- Wait-for-reply mode (`send --wait`) with a timeout.

## About the author

*Leo ([@runes_leo](https://x.com/runes_leo)) — AI × Crypto independent builder. Trading on [Polymarket](https://polymarket.com/?via=runes-leo&r=runesleo&utm_source=github&utm_content=grok-bot-bridge), building data and content pipelines with Claude Code and Codex.*

*[leolabs.me](https://leolabs.me) — writing · community · open-source tools · indie projects · all platforms.*

*[X Subscription](https://x.com/runes_leo/creator-subscriptions/subscribe) — paid content weekly, or just buy me a coffee 😁*

*Learn in public, Build in public.*

## License

MIT
