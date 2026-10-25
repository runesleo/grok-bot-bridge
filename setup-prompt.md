# Setup prompt for your Grok Bot

Send this, as is, in the chat of each Bot that should take tasks (once per Bot). 中文版见 [setup-prompt.zh.md](setup-prompt.zh.md).

---

Please create a routine for yourself named "Task Inbox". No schedule; add only a Webhook trigger.
Write the routine's instruction as:
"When the webhook fires, read the job_id and task fields from the request JSON. Do only what task says, nothing else; do not post, reply, like, or touch wallets or account settings. When done, reply in this chat with one message whose first line is exactly: BRIDGE_RESULT <job_id>, with the result from the second line on. If you have already replied BRIDGE_RESULT for the same job_id, reply only: BRIDGE_DUP <job_id>, and do not redo it."
When it is ready, reply: BRIDGE_ROUTINE_READY + the routine name. Do not paste the webhook key in the chat.

---

The Bot answers `BRIDGE_ROUTINE_READY Task Inbox` when done.

Keep the line "do not post, reply, like, or touch wallets or account settings": any program holding the key can push any text into this inbox. That line lowers the risk but is not a hard limit, so don't give this Bot posting, wallet or account tools.
