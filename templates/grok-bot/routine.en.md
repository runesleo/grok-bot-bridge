# Grok Bot receiver (English draft)

Paste the block below into the Bot that should receive tasks. One Bot, one paste. Do not publish this draft to x.ai from here.

---

Please create a routine for yourself named "Task Inbox". No schedule; add only a Webhook trigger.
Write the routine's instruction as:
"When the webhook fires, read the job_id and task fields from the request JSON. Do only what task says, nothing else; do not post, reply, like, or touch wallets or account settings. When done, reply in this chat with one message whose first line is exactly: BRIDGE_RESULT <job_id>, with the result from the second line on. If you have already replied BRIDGE_RESULT for the same job_id, reply only: BRIDGE_DUP <job_id>, and do not redo it."
When the routine is ready, reply: BRIDGE_ROUTINE_READY Task Inbox. Do not paste the webhook key in the chat.

---

The Bot answers `BRIDGE_ROUTINE_READY Task Inbox` when the routine exists.

Keep the line about posts, replies, likes, wallets, and account settings. Any program that holds the key can push any text into this inbox. That line lowers the risk. It is not a hard limit, so do not give this Bot posting, wallet, or account tools.
