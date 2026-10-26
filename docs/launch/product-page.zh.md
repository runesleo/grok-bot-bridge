# Grok Bot Bridge

产品页草稿。先放在仓库里，你决定上站再发。

你把一件活交给自己的 Grok Bot。同一个任务编号只发一次。做完的结果回到派活的那个 AI。

## 和 Bridge Bot 的差别

[Bridge Bot](https://x.ai/bot/GHoerhXVqIMYC2VmYI_fZ)（Moritz）把活派出去。

| | Bridge Bot | Grok Bot Bridge |
| --- | --- | --- |
| 只发一次 | 把活派出去 | 同一个任务编号只发一次。你的电脑挡住重复发送。真的又送到时，Bot 回 `BRIDGE_DUP`。 |
| 结果收回 | 派出去就结束 | Bot 回 `BRIDGE_RESULT <编号>`。一条命令写成 `results/<编号>.md`，交给派活的那个 AI。 |
| 开源 | x.ai 上的一个 Bot | MIT 源码：https://github.com/runesleo/grok-bot-bridge |

## 怎么试

克隆 https://github.com/runesleo/grok-bot-bridge ，在目录里执行 `claude --plugin-dir .`。

两条命令：`/send-to-grok-bot` 和 `/grok-bot-results`。

第一次运行会在你电脑上建 `~/.grok-bridge/bots.env`（权限 600），等你把自己的 webhook 地址和钥匙写进去。钥匙留在这个文件里。

接收端安装 https://x.ai/bot/nnPi-WVku_162DIxfqZ3Z 。可改的中英草稿在 `templates/grok-bot/`。
