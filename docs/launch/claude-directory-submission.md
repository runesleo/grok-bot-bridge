# Claude 插件目录提交材料（草稿）

不要提交。不要打开 https://claude.ai/directory/manage 点 Submit。不要 push，不要发帖，不要写价格。

门户步骤按 2026-10-26 读过的 https://www.claude.com/docs/plugins/submit 。每个插件单独交一次。仓库在上线前要公开。校验命令（在插件目录的上一级跑）：`claude plugin validate ./grok-bot-bridge`。清单在仓库根的 `.claude-plugin/plugin.json`，所以 Plugin path 留空。

## Source

| 字段 | 填写 |
| --- | --- |
| What would you like to submit? | Plugin bundle |
| Repository | `https://github.com/runesleo/grok-bot-bridge` 或 `runesleo/grok-bot-bridge` |
| Plugin path | 留空。`.claude-plugin/plugin.json` 在仓库根。 |
| Branch or tag | 留空，跟踪默认分支。先把 `product/one-click` 合并进默认分支，再来交。不要把 `product/one-click` 填进门户。 |

Validate 通过后再往下。推了新提交就要重新 Validate。这次不要点。

## Listing

门户从 `plugin.json` 和 `README.md` 读展示文案。要改就改这两处，再 Validate。

| 字段 | 值 |
| --- | --- |
| name | `grok-bot-bridge`（清单 `name`。展示名 `displayName` 是 `Grok Bot Task Inbox`） |
| version | `0.3.0`（随这次功能写在清单里，还没打 tag） |
| description | Send a task to your Grok Bot once, then collect the BRIDGE_RESULT reply. |
| license | MIT（仓库根 `LICENSE`） |
| author | Leo，https://leolabs.me |
| homepage / repository | https://github.com/runesleo/grok-bot-bridge |

## Data handling

提交前你再看一遍这四条。下面是按当前代码写的草稿答案。

1. 会不会读取或保存个人数据：会。任务正文是用户自己写的。插件不从本机文件读 webhook 地址和钥匙：Claude Code 启用插件时询问，地址是普通 `userConfig`，钥匙是 `sensitive: true`，进系统安全存储。随插件打包的本地 MCP 只在进程环境里拿到这两项，命令正文里没有钥匙。单独运行 `grok_bridge.py` 时，地址和钥匙仍可以在 `~/.grok-bridge/bots.env`（设了 `GROK_BRIDGE_HOME` 就在那个目录的 `bots.env`，新建时权限 600）。账本和 `results/<job_id>.md` 在本机。`harvest` 只读本机 Grok Bot macOS 应用留下的对话副本。没有自己的服务器，不上传配置。
2. 会不会把数据发到已声明连接器以外的地方：会把 `{job_id, task}` POST 到用户填进插件选项的那个 https webhook（单独跑脚本时，是脚本配置里的那个），也就是用户自己的 Grok Bot。别处不发。没有远程 MCP。本地 MCP 只是随包脚本。地址不是 `https://` 就拒发，避免钥匙走明文。README 的 Privacy 段写了同一件事。
3. 留多久：留在用户自己的电脑上，直到他们删掉配置目录里的账本和结果。插件侧没有服务器，也就没有另一份保存期限。
4. 是否面向 18 岁以下：否。给自己的编程代理派活用。

## Compliance

- 联系邮箱：填你在 claude.ai 上能收到信的那个。本草稿不写地址。
- 四项确认：你在门户里自己勾。这里不代勾。

## Review and submit

- 新版本怎么进来：默认 GitHub push webhook。现在不设置。
- 不要点 Submit for review，也不要 Publish。
