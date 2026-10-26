#!/usr/bin/env python3
"""Grok Bot Bridge: let Claude Code / any script hand tasks to your Grok Bots, once, and get the answers back.

  setup    Create ~/.grok-bridge/bots.env (mode 600) when it is missing.
           Prints READY or NEED_WEBHOOK. Never prints the webhook URL or key.
  send     POST {job_id, task} to a Bot's webhook routine. Each job_id goes out at most once;
           a timeout is recorded as UNKNOWN and never retried automatically.
           --url and --key supply the pair and skip the config file.
  harvest  Read the Grok Bot desktop app's local chat copies (macOS) for replies that start
           with `BRIDGE_RESULT <job_id>`, save each to results/<job_id>.md, mark it REPLIED.
  status   Show the latest ledger row for a job.
  mcp      Stdio MCP for the Claude Code plugin. Uses BRIDGE_PLUGIN_URL and BRIDGE_PLUGIN_KEY
           from the environment. Does not read the config file.

Running this file yourself: ~/.grok-bridge/bots.env, one pair per Bot (chmod 600):
  BRIDGE_URL_RESEARCH=https://...      BRIDGE_KEY_RESEARCH=...
Set GROK_BRIDGE_HOME to move the config, ledger, and results together.
The Claude Code plugin does not read that file. Claude Code asks for bridge_url and bridge_key.
Standard library only. Python 3.9+.
"""
from __future__ import annotations

import argparse, base64, glob, json, os, re, sys, time, urllib.request
from pathlib import Path

HOME = Path(os.environ.get("GROK_BRIDGE_HOME") or Path.home() / ".grok-bridge")
ENV, LEDGER, RESULTS = HOME / "bots.env", HOME / "sent.jsonl", HOME / "results"
APP_STORE = Path.home() / "Library/Application Support/Grok Bot/sand-client-persistence"
RESULT_RE = re.compile(r"BRIDGE_RESULT\s+(\S+)\s*$")
JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")  # also a safe file name
PLUGIN_VERSION = "0.3.0"
PLUGIN_BOT = "INBOX"


_CONFIG_STUB = (
    "# Local config for grok-bot-bridge. One pair per Bot.\n"
    "# Edit this file on your machine. Do not commit it. Do not paste the key into chat.\n"
    "# BRIDGE_URL_RESEARCH=\n"
    "# BRIDGE_KEY_RESEARCH=\n"
)


def load_env(path=None) -> dict:
    if path is None:
        path = ENV
    if not path.exists():
        raise SystemExit(
            "no config: run `grok_bridge.py setup`, then fill BRIDGE_URL_<NAME> and "
            "BRIDGE_KEY_<NAME> in ~/.grok-bridge/bots.env (or bots.env under GROK_BRIDGE_HOME). "
            "Do not paste the key into chat."
        )
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def bot_names(env: dict) -> list[str]:
    """Bot names that have both an https URL and a key. The values are not returned."""
    found = []
    for key, url in env.items():
        if not key.startswith("BRIDGE_URL_"):
            continue
        name = key[len("BRIDGE_URL_"):]
        if name and isinstance(url, str) and url.startswith("https://") and env.get(f"BRIDGE_KEY_{name}"):
            found.append(name)
    return sorted(found)


def ensure_local_config(home: Path | None = None) -> dict:
    """Create bots.env (mode 600) when missing. Status only: never the URL or the key."""
    home = HOME if home is None else Path(home)
    env_path = home / "bots.env"
    created = False
    if not env_path.exists():
        made_dir = not home.exists()
        home.mkdir(parents=True, exist_ok=True)
        if made_dir:
            os.chmod(home, 0o700)
        try:
            fd = os.open(env_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            pass
        else:
            try:
                os.write(fd, _CONFIG_STUB.encode())
            finally:
                os.close(fd)
            os.chmod(env_path, 0o600)
            created = True
    env = load_env(env_path) if env_path.is_file() else {}
    names = bot_names(env)
    return {"status": "READY" if names else "NEED_WEBHOOK", "created": created, "bots": names}


def rows(ledger=LEDGER) -> list[dict]:
    if not ledger.exists():
        return []
    out = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def _append(ledger, row) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def post(url, key, body, timeout=30) -> int:
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {key}", "content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def send(bot, job_id, task, *, ledger=None, env=None, poster=None) -> dict:
    if ledger is None:
        ledger = LEDGER
    if poster is None:
        poster = post
    if not JOB_ID_RE.match(job_id):
        return {"job_id": job_id, "status": "BAD_JOB_ID"}
    # UNKNOWN counts as sent: the Bot may have it already. Only a refused send may go again.
    if any(r.get("job_id") == job_id and r.get("status") in ("SENT", "UNKNOWN") for r in rows(ledger)):
        return {"job_id": job_id, "status": "ALREADY_SENT"}
    env = env if env is not None else load_env()
    url, key = env.get(f"BRIDGE_URL_{bot.upper()}"), env.get(f"BRIDGE_KEY_{bot.upper()}")
    if not (url and key):
        return {"job_id": job_id, "status": "NO_WEBHOOK"}
    if not url.startswith("https://"):
        return {"job_id": job_id, "status": "NOT_HTTPS"}  # never send the key in clear text
    try:
        code = poster(url, key, {"job_id": job_id, "task": task})
    except Exception as e:  # noqa: BLE001 - outcome unknown: record it, never resend blindly
        code = getattr(e, "code", None)
        st = "UNKNOWN" if code is None else "FAILED"
    else:
        st = "SENT" if 200 <= code < 300 else "FAILED"
    _append(ledger, {"ts": int(time.time()), "job_id": job_id, "bot": bot, "http": code, "status": st})
    return {"job_id": job_id, "status": st, "http": code}


def _slice_name(path: str) -> str:
    n = os.path.basename(path)[:-5]
    try:
        return base64.b32decode(n.upper() + "=" * (-len(n) % 8)).decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""


def _objects(raw: str):
    """The app's .blob files hold JSON message objects behind a binary header; brace-match them out."""
    for m in re.finditer(r'\{"kind"\s*:\s*"send-message"', raw):
        depth, i, in_str, esc = 0, m.start(), False, False
        while i < len(raw):
            c = raw[i]
            if in_str:
                esc, in_str = (False, in_str) if esc else (c == "\\", c != '"')
            elif c == '"':
                in_str = True
            elif c in "{}":
                depth += 1 if c == "{" else -1
                if depth == 0:
                    break
            i += 1
        try:
            yield json.loads(raw[m.start(): i + 1])
        except ValueError:
            continue


def local_replies(store=APP_STORE) -> list[dict]:
    """Assistant messages from every Grok Bot chat saved on this Mac. Read-only."""
    out = []
    for f in glob.glob(str(store / "*.blob")):
        if "transcript.replicas" not in _slice_name(f):
            continue
        raw = open(f, "rb").read().decode("utf-8", "replace")
        for obj in _objects(raw):
            body = (obj.get("message") or {}).get("content")
            if isinstance(body, str) and body.strip():
                out.append({"content": body, "ts": obj.get("timestampMs") or 0})
    return sorted(out, key=lambda r: r["ts"])


def harvest(*, ledger=LEDGER, results=RESULTS, reader=local_replies) -> list[str]:
    rs = rows(ledger)
    waiting = {r["job_id"] for r in rs if r.get("status") in ("SENT", "UNKNOWN")}
    waiting -= {r["job_id"] for r in rs if r.get("status") == "REPLIED"}
    waiting = {j for j in waiting if JOB_ID_RE.match(j)}
    got = []
    for msg in (reader() if waiting else []):
        text = msg["content"].strip()
        m = RESULT_RE.match(text.splitlines()[0].strip())
        if not m or m.group(1) not in waiting:
            continue
        job_id = m.group(1)
        waiting.discard(job_id)
        results.mkdir(parents=True, exist_ok=True)
        out = results / f"{job_id}.md"
        out.write_text(text + "\n", encoding="utf-8")
        _append(ledger, {"ts": int(time.time()), "job_id": job_id, "status": "REPLIED", "result": f"{job_id}.md"})
        got.append(job_id)
    return got


def _present(value: str | None) -> str:
    text = (value or "").strip()
    if not text or "${" in text:
        return ""
    return text


def send_configured(url, key, job_id, task, *, ledger=None, poster=None) -> dict:
    """Send one explicit pair. Never reads the config file."""
    url, key = _present(url), _present(key)
    env = {f"BRIDGE_URL_{PLUGIN_BOT}": url, f"BRIDGE_KEY_{PLUGIN_BOT}": key}
    return send(PLUGIN_BOT, job_id, task, ledger=ledger, env=env, poster=poster)


_SEND_TOOL = {
    "name": "send_task",
    "description": (
        "Post one task to the Grok Bot webhook saved in this plugin's options. "
        "Does not read a credential file. The same job id is sent at most once."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "job_id": {"type": "string"},
            "task": {"type": "string"},
        },
        "required": ["job_id", "task"],
        "additionalProperties": False,
    },
}


def mcp_send_task(arguments) -> tuple[str, bool]:
    if not isinstance(arguments, dict):
        arguments = {}
    job_id, task = arguments.get("job_id"), arguments.get("task")
    if not isinstance(job_id, str) or not isinstance(task, str):
        return json.dumps({"status": "BAD_JOB_ID"}, ensure_ascii=False), True
    result = send_configured(
        os.environ.get("BRIDGE_PLUGIN_URL"),
        os.environ.get("BRIDGE_PLUGIN_KEY"),
        job_id,
        task,
    )
    failed = result.get("status") in {"NO_WEBHOOK", "NOT_HTTPS", "BAD_JOB_ID", "FAILED"}
    return json.dumps(result, ensure_ascii=False), failed


def mcp_handle(msg: dict) -> dict | None:
    if not isinstance(msg, dict):
        return None
    method, mid = msg.get("method"), msg.get("id")
    if isinstance(method, str) and method.startswith("notifications/"):
        return None
    if method == "initialize":
        requested = (msg.get("params") or {}).get("protocolVersion")
        version = requested if isinstance(requested, str) and requested else "2024-11-05"
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "grok-bot-bridge", "version": PLUGIN_VERSION},
        }}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": [_SEND_TOOL]}}
    if method == "tools/call":
        params = msg.get("params") or {}
        name = params.get("name")
        if name != "send_task":
            return {"jsonrpc": "2.0", "id": mid, "result": {
                "content": [{"type": "text", "text": "unknown tool"}], "isError": True,
            }}
        text, failed = mcp_send_task(params.get("arguments") or {})
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": text}], "isError": failed,
        }}
    if mid is not None:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": "method not found"}}
    return None


def mcp_serve() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        try:
            reply = mcp_handle(msg)
        except Exception:  # noqa: BLE001 - never print the URL, the key, or the traceback
            reply = {"jsonrpc": "2.0", "id": msg.get("id") if isinstance(msg, dict) else None,
                     "error": {"code": -32603, "message": "internal error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("setup", help="create a local bots.env if missing; prints status only")
    s = sub.add_parser("send")
    s.add_argument("--url", default=None, help="webhook URL; if set with or without --key, do not read the config file")
    s.add_argument("--key", default=None, help="webhook key; if set with or without --url, do not read the config file")
    s.add_argument("bot", help="name used in bots.env, e.g. research")
    s.add_argument("job_id", help="unique id for this task")
    s.add_argument("task", nargs="?", help="task text; omit to read stdin")
    sub.add_parser("harvest")
    sub.add_parser("mcp", help="stdio MCP for the Claude Code plugin; does not read the config file")
    st = sub.add_parser("status")
    st.add_argument("job_id")
    a = ap.parse_args()
    if a.cmd == "setup":
        print(json.dumps(ensure_local_config(), ensure_ascii=False))
        return 0
    if a.cmd == "mcp":
        return mcp_serve()
    if a.cmd == "send":
        task = a.task if a.task is not None else sys.stdin.read()
        if a.url is not None or a.key is not None:
            env = {f"BRIDGE_URL_{a.bot.upper()}": a.url or "", f"BRIDGE_KEY_{a.bot.upper()}": a.key or ""}
            res = send(a.bot, a.job_id, task, env=env)
        else:
            res = send(a.bot, a.job_id, task)
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res["status"] in ("SENT", "ALREADY_SENT") else 1
    if a.cmd == "harvest":
        if not APP_STORE.is_dir():
            print("Grok Bot macOS app chat copies were not found; harvest needs that app on this Mac", file=sys.stderr)
            return 2
        print(json.dumps({"collected": harvest()}, ensure_ascii=False))
        return 0
    hits = [r for r in rows() if r.get("job_id") == a.job_id]
    print(json.dumps(hits[-1] if hits else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
