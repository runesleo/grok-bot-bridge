# Grok Bot Bridge

Draft for a product page. It stays in the repo until you publish it.

You send a task to your own Grok Bot. The same job id goes out once. The answer comes back to the agent that sent the task.

## Compared with Bridge Bot

[Bridge Bot](https://x.ai/bot/GHoerhXVqIMYC2VmYI_fZ) (Moritz) dispatches a task.

| | Bridge Bot | Grok Bot Bridge |
| --- | --- | --- |
| Send once | Dispatches the task | The same job id goes out once. Your machine blocks a repeat. If one still arrives, the bot answers `BRIDGE_DUP`. |
| Result back | The handoff ends at dispatch | The bot answers `BRIDGE_RESULT <job_id>`. One command writes `results/<job_id>.md` for the agent that sent the task. |
| Open source | A bot on x.ai | MIT source: https://github.com/runesleo/grok-bot-bridge |

## Try it

Clone https://github.com/runesleo/grok-bot-bridge and load that folder with `claude --plugin-dir .`.

Two commands: `/send-to-grok-bot` and `/grok-bot-results`.

The first run creates `~/.grok-bridge/bots.env` on your machine (mode 600) and waits while you fill in your webhook URL and key. The key stays in that file.

For the bot that receives tasks, install https://x.ai/bot/nnPi-WVku_162DIxfqZ3Z. Editable English and Chinese drafts are in `templates/grok-bot/`.
