# Grok Bot Bridge

**让 Claude Code、ChatGPT 或你自己的脚本把活派给 Grok Bot：每件活只发一次，做完的结果一条命令收回来存成文件。**

![license](https://img.shields.io/badge/license-MIT-blue) ![python](https://img.shields.io/badge/python-3.9%2B-blue) ![deps](https://img.shields.io/badge/dependencies-none-green)

[English](README.md)

## 你能得到什么

- **每个 Bot 一个派活入口。** 发一段话给 Bot，它自己把 webhook 例行任务建好，不用你去设置里点。
- **只发一次。** 每件活带一个单号，本机记一本账：同一个单号只发一次；发出去超时、不确定有没有送到，就记成「不确定」（`UNKNOWN`），不会自动重发。Bot 那边也认单号，重复投递时只回「这单做过了」（`BRIDGE_DUP`）。
- **结果一条命令收回。** Bot 做完回一条以 `BRIDGE_RESULT <单号>` 开头的消息，`harvest` 把它存成 `results/<单号>.md`，账本上同时标成「已回」。
- **一个文件，零依赖。** 只用 Python 自带的库。

## 为什么做这个

用程序往 Grok Bot 窗口里填字派活很脆：程序读不到回复，就以为没发出去，于是一遍遍重发。我自己有一单在 5 小时里被重发了 17 次，其中 15 次其实早就送到了。换成 webhook 加单号以后，派活从「碰运气」变成「有回执」。

## 怎么运转

```text
你的 AI ──send(Bot, 单号, 任务)──▶ Grok Bot 的派活入口（webhook 例行任务）
   ▲                                      │ 做活
   │                                      ▼
results/<单号>.md ◀──harvest── Bot 对话里的「BRIDGE_RESULT <单号>\n…」
```

## 三步装好

1. **装一个自带入口的 Bot。** 直接装现成模板：https://x.ai/bot/nnPi-WVku_162DIxfqZ3Z （「派活入口 · Task Inbox」）。想给已有的 Bot 加入口，就把 [setup-prompt.zh.md](setup-prompt.zh.md) 里的那段话发给它。
2. **拿到入口地址和密钥。** 在 Grok Bot 桌面版里打开这个 Bot 的详情 → 例行任务，**右键**「派活入口」那一行 → Webhook，复制「Webhook URL」和「Webhook 密钥」，写进 `~/.grok-bridge/bots.env`（名字自己起，一个 Bot 一对）：

   ```
   BRIDGE_URL_RESEARCH=<Webhook URL>
   BRIDGE_KEY_RESEARCH=<Webhook 密钥>
   ```

   ```bash
   mkdir -p ~/.grok-bridge && touch ~/.grok-bridge/bots.env && chmod 600 ~/.grok-bridge/bots.env
   ```

   然后打开这个文件，把上面两行贴进去。

3. **拿脚本。**

   ```bash
   git clone https://github.com/runesleo/grok-bot-bridge.git
   ```

   ```bash
   cd grok-bot-bridge
   ```

让 AI 帮你装：把 [install.md](install.md) 丢给 Claude Code / Codex，它会照着一步步做。

## 上手

```bash
python3 grok_bridge.py send research job-001 "只回一行：现在北京时间几点。"
```

```bash
python3 grok_bridge.py harvest
```

```bash
python3 grok_bridge.py status job-001
```

在 Claude Code 里把这个仓库装成插件。清单在仓库根的 `.claude-plugin/plugin.json`。

- `/send-to-grok-bot` 走 `send`。同一个单号只发一次。
- `/grok-bot-results` 走 `harvest`，再读 `results/<单号>.md`。

第一次运行会执行 `python3 grok_bridge.py setup`。本机还没有 `~/.grok-bridge/bots.env` 时，它会建一个权限 600 的空文件，然后让你在自己电脑上把 webhook 地址和钥匙写进去。从 Grok Bot 应用里复制。命令不会让你把钥匙贴进对话，脚本也不会把钥匙打出来。

```bash
git clone https://github.com/runesleo/grok-bot-bridge.git
cd grok-bot-bridge
claude --plugin-dir .
```

## 需要什么

- Python 3.9 以上。
- 能建例行任务和 webhook 触发的 Grok Bot。
- `harvest` 要在装了 **Grok Bot macOS 桌面版**的同一台 Mac 上跑：它只读 App 存在本机的对话副本，不改任何东西。

**隐私：** 密钥等于这个入口的钥匙，不要贴进聊天、截图或公开仓库。配置、账本和结果都在 `~/.grok-bridge/`（设置 `GROK_BRIDGE_HOME` 会把这三样一起换位置）；入口地址不是 `https://` 开头的，脚本直接拒发，除了你配置的 webhook，不往任何地方发数据。

## 实测

2026-10-25，同一个账号下 3 个 Bot：简单的活大约 1 分钟回来；一件要分析一周推文的活 12 分钟回来；同一个单号重复发送在本机就被拦下，偶尔漏过去的那次 Bot 也只回了 `BRIDGE_DUP`。`python3 -m pytest -q test_grok_bridge.py` 全部用假数据离线跑，不会真的往 Bot 发东西。

## 已知限制（v0.1）

- `harvest` 读的是桌面版的本机存储，不是官方公开接口，App 更新后可能要跟着改；`send` 走官方 webhook，不受影响。
- `harvest` 只支持 macOS，其他系统请在 App 里看回复。
- 「只做投进来的事、不发帖不点赞不碰钱包」是写给 Bot 的指令，不是硬限制。接活的 Bot 别给它开发帖、钱包、账号这类工具，密钥当密码保管。
- `harvest` 按单号在本机所有对话里找回复，不区分是哪个 Bot 回的，谁先打出 `BRIDGE_RESULT <单号>` 就收谁的。单号要唯一、别人猜不到（比如 `<任务名>-<时间>-<随机串>`）；结果文件当作外部内容来读，别直接当指令喂给 AI。
- Bot 回复的第一行必须是 `BRIDGE_RESULT <单号>`，不是的话收不回来。

## 接下来

- `send --wait`：发完等着收结果，带超时。

## 关于作者

*Leo（[@runes_leo](https://x.com/runes_leo)）— AI × Crypto 独立构建者。在 [Polymarket](https://polymarket.com/?via=runes-leo&r=runesleo&utm_source=github&utm_content=grok-bot-bridge) 做量化，用 Claude Code 和 Codex 搭数据与内容管线。*

*[leolabs.me](https://leolabs.me) — 写作 · 社群 · 开源工具 · 独立项目*

*[X 订阅](https://x.com/runes_leo/creator-subscriptions/subscribe) — 付费内容周刊*

*Learn in public, Build in public.*

## 许可

MIT
