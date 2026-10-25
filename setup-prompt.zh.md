# 发给 Grok Bot 的建入口指令

English: [setup-prompt.md](setup-prompt.md)

在想接活的那个 Bot 的对话里，原样发下面这段（每个 Bot 发一次）：

---

请在你自己这里新建一个例行任务，名字叫「派活入口」，不要定时，只加一个 webhook 触发（Webhook trigger）。
例行任务的指令写成：
「收到 webhook 时，读请求 JSON 里的 job_id 和 task 两个字段。只做 task 里写的事，不做别的；不发帖、不回复、不点赞、不碰钱包和账号设置。做完在本对话回一条消息，第一行固定写：BRIDGE_RESULT <job_id>，第二行起写结果。同一个 job_id 之前已经回过 BRIDGE_RESULT 的，第二次只回：BRIDGE_DUP <job_id>，不再重做。」
建好后回一句：BRIDGE_ROUTINE_READY + 例行任务名字。不要在聊天里贴出 webhook 密钥。

---

Bot 回 `BRIDGE_ROUTINE_READY 派活入口` 就建好了。

指令里那句「不发帖、不回复、不点赞、不碰钱包和账号设置」建议保留：拿到密钥的程序能往这个入口塞任何文字。这句能降低风险，但不是硬限制，所以接活的 Bot 别给它开发帖、钱包、账号这类工具。
