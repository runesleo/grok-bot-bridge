#!/usr/bin/env python3
"""Grok Bot Bridge: let Claude Code / any script hand tasks to your Grok Bots, once, and get the answers back.

  send     POST {job_id, task} to a Bot's webhook routine. Each job_id goes out at most once;
           a timeout is recorded as UNKNOWN and never retried automatically.
  harvest  Read the Grok Bot desktop app's local chat copies (macOS) for replies that start
           with `BRIDGE_RESULT <job_id>`, save each to results/<job_id>.md, mark it REPLIED.
  status   Show the latest ledger row for a job.

Config: ~/.grok-bridge/bots.env, one pair per Bot (chmod 600):
  BRIDGE_URL_RESEARCH=https://...      BRIDGE_KEY_RESEARCH=...
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


def load_env(path=ENV) -> dict:
    if not path.exists():
        raise SystemExit(f"no config: create {path} with BRIDGE_URL_<NAME>= / BRIDGE_KEY_<NAME>= (see README)")
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


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


def send(bot, job_id, task, *, ledger=LEDGER, env=None, poster=post) -> dict:
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
        _append(ledger, {"ts": int(time.time()), "job_id": job_id, "status": "REPLIED", "result": str(out)})
        got.append(job_id)
    return got


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("send")
    s.add_argument("bot", help="name used in bots.env, e.g. research")
    s.add_argument("job_id", help="unique id for this task")
    s.add_argument("task", nargs="?", help="task text; omit to read stdin")
    sub.add_parser("harvest")
    st = sub.add_parser("status")
    st.add_argument("job_id")
    a = ap.parse_args()
    if a.cmd == "send":
        res = send(a.bot, a.job_id, a.task if a.task is not None else sys.stdin.read())
        print(json.dumps(res, ensure_ascii=False))
        return 0 if res["status"] in ("SENT", "ALREADY_SENT") else 1
    if a.cmd == "harvest":
        if not APP_STORE.is_dir():
            print(f"Grok Bot desktop app data not found at {APP_STORE}; harvest needs the macOS app", file=sys.stderr)
            return 2
        print(json.dumps({"collected": harvest()}, ensure_ascii=False))
        return 0
    hits = [r for r in rows() if r.get("job_id") == a.job_id]
    print(json.dumps(hits[-1] if hits else None, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
