import base64, json, re, struct, sys
from pathlib import Path
import grok_bridge as g

ROOT = Path(__file__).resolve().parent

ENV = {"BRIDGE_URL_RESEARCH": "https://example.invalid/hook", "BRIDGE_KEY_RESEARCH": "k"}


def test_send_once_and_unknown_not_counted(tmp_path):
    led, calls = tmp_path / "sent.jsonl", []
    ok = lambda u, k, b: calls.append(b) or 200
    assert g.send("research", "j1", "t", ledger=led, env=ENV, poster=ok)["status"] == "SENT"
    assert g.send("research", "j1", "t", ledger=led, env=ENV, poster=ok)["status"] == "ALREADY_SENT"
    assert len(calls) == 1

    def boom(u, k, b):
        raise TimeoutError()
    assert g.send("research", "j2", "t", ledger=led, env=ENV, poster=boom)["status"] == "UNKNOWN"
    assert g.send("research", "j2", "t", ledger=led, env=ENV, poster=ok)["status"] == "ALREADY_SENT"  # UNKNOWN is never resent
    assert len(calls) == 1
    assert g.send("other", "j3", "t", ledger=led, env=ENV, poster=ok)["status"] == "NO_WEBHOOK"
    assert g.send("research", "../../x", "t", ledger=led, env=ENV, poster=ok)["status"] == "BAD_JOB_ID"
    plain = {"BRIDGE_URL_RESEARCH": "http://example.invalid/hook", "BRIDGE_KEY_RESEARCH": "k"}
    assert g.send("research", "j4", "t", ledger=led, env=plain, poster=ok)["status"] == "NOT_HTTPS"
    assert len(calls) == 1


def test_harvest_from_app_store(tmp_path):
    led, res, store = tmp_path / "sent.jsonl", tmp_path / "results", tmp_path / "store"
    store.mkdir()
    g.send("research", "j5", "t", ledger=led, env=ENV, poster=lambda u, k, b: 200)
    name = base64.b32encode(b"acct.transcript.replicas.abc").decode().rstrip("=").lower()
    msgs = [{"kind": "send-message", "timestampMs": 1, "message": {"type": "text", "content": "BRIDGE_DUP j5"}},
            {"kind": "send-message", "timestampMs": 2, "message": {"type": "text", "content": "BRIDGE_RESULT j5\n结果 {x}"}}]
    blob = b"\x00\x01hdr" + "".join(json.dumps(m, ensure_ascii=False) for m in msgs).encode()
    (store / f"{name}.blob").write_bytes(blob)
    assert g.harvest(ledger=led, results=res, reader=lambda: g.local_replies(store)) == ["j5"]
    assert "结果 {x}" in (res / "j5.md").read_text(encoding="utf-8")
    replied = [json.loads(line) for line in led.read_text(encoding="utf-8").splitlines()]
    assert replied[-1]["result"] == "j5.md"
    assert g.harvest(ledger=led, results=res, reader=lambda: g.local_replies(store)) == []


def test_duplicate_marker_is_not_a_result(tmp_path):
    led, res = tmp_path / "sent.jsonl", tmp_path / "results"
    assert g.send("research", "j6", "t", ledger=led, env=ENV, poster=lambda u, k, b: 200)["status"] == "SENT"
    assert g.send("research", "j6", "again", ledger=led, env=ENV, poster=lambda u, k, b: 200)["status"] == "ALREADY_SENT"
    assert g.harvest(ledger=led, results=res, reader=lambda: [{"content": "BRIDGE_DUP j6", "ts": 1}]) == []
    assert not (res / "j6.md").exists()
    assert g.harvest(ledger=led, results=res, reader=lambda: [{"content": "BRIDGE_RESULT j6\nok", "ts": 2}]) == ["j6"]
    assert (res / "j6.md").read_text(encoding="utf-8").startswith("BRIDGE_RESULT j6\n")


def test_setup_creates_private_stub_and_hides_values(tmp_path, monkeypatch, capsys):
    home = tmp_path / "fresh"
    monkeypatch.setattr(g, "HOME", home)
    monkeypatch.setattr(sys, "argv", ["grok_bridge.py", "setup"])
    assert g.main() == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {"status": "NEED_WEBHOOK", "created": True, "bots": []}
    env_path = home / "bots.env"
    assert (env_path.stat().st_mode & 0o777) == 0o600
    assert (home.stat().st_mode & 0o777) == 0o700
    stub = env_path.read_text(encoding="utf-8")
    assert "https://" not in stub
    assert "/Users/" not in stub
    assert "BRIDGE_KEY_RESEARCH=" in stub

    env_path.write_text(
        "BRIDGE_URL_RESEARCH=https://example.invalid/hook\nBRIDGE_KEY_RESEARCH=fixture-key\n",
        encoding="utf-8",
    )
    again = g.ensure_local_config(home)
    assert again == {"status": "READY", "created": False, "bots": ["RESEARCH"]}
    assert "fixture-key" not in json.dumps(again)
    assert "example.invalid" not in json.dumps(again)
    assert "fixture-key" in env_path.read_text(encoding="utf-8")

    clear = tmp_path / "clear"
    clear.mkdir()
    (clear / "bots.env").write_text(
        "BRIDGE_URL_RESEARCH=http://example.invalid/hook\nBRIDGE_KEY_RESEARCH=fixture-key\n",
        encoding="utf-8",
    )
    refused = g.ensure_local_config(clear)
    assert refused["status"] == "NEED_WEBHOOK"
    assert "fixture-key" not in json.dumps(refused)
    assert "example.invalid" not in json.dumps(refused)

    calls = []
    bare = tmp_path / "bare"
    assert g.ensure_local_config(bare)["status"] == "NEED_WEBHOOK"
    assert g.send(
        "research", "j9", "t", ledger=tmp_path / "sent.jsonl", env=g.load_env(bare / "bots.env"),
        poster=lambda u, k, b: calls.append(b) or 200,
    )["status"] == "NO_WEBHOOK"
    assert calls == []


def _no_file(*_a, **_k):
    raise AssertionError("read config file")


def test_configured_send_never_reads_config_file(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "load_env", _no_file)
    calls = []
    res = g.send_configured(
        "https://example.invalid/hook", "secret-key", "j10", "hello",
        ledger=tmp_path / "sent.jsonl", poster=lambda u, k, b: calls.append((u, k, b)) or 200,
    )
    assert res["status"] == "SENT"
    assert calls == [("https://example.invalid/hook", "secret-key", {"job_id": "j10", "task": "hello"})]
    assert "secret-key" not in json.dumps(res)
    assert "example.invalid" not in json.dumps(res)


def test_unsubstituted_plugin_option_is_not_sent(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "load_env", _no_file)
    calls = []
    res = g.send_configured(
        "${user_config.bridge_url}", "${user_config.bridge_key}", "j11", "t",
        ledger=tmp_path / "sent.jsonl", poster=lambda u, k, b: calls.append(b) or 200,
    )
    assert res["status"] == "NO_WEBHOOK"
    assert calls == []


def test_cli_send_without_flags_reads_config_file(tmp_path, monkeypatch, capsys):
    env_path = tmp_path / "bots.env"
    env_path.write_text(
        "BRIDGE_URL_RESEARCH=https://example.invalid/hook\nBRIDGE_KEY_RESEARCH=k\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(g, "ENV", env_path)
    monkeypatch.setattr(g, "LEDGER", tmp_path / "sent.jsonl")
    monkeypatch.setattr(g, "post", lambda u, k, b, timeout=30: 200)
    monkeypatch.setattr(sys, "argv", ["grok_bridge.py", "send", "research", "j7", "t"])
    assert g.main() == 0
    assert json.loads(capsys.readouterr().out)["status"] == "SENT"


def test_cli_send_flags_skip_config_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(g, "load_env", _no_file)
    monkeypatch.setattr(g, "LEDGER", tmp_path / "sent.jsonl")
    seen = []
    monkeypatch.setattr(g, "post", lambda u, k, b, timeout=30: seen.append((u, k)) or 200)
    monkeypatch.setattr(sys, "argv", [
        "grok_bridge.py", "send", "--url", "https://example.invalid/hook", "--key", "k",
        "research", "j8", "t",
    ])
    assert g.main() == 0
    assert seen == [("https://example.invalid/hook", "k")]
    assert json.loads(capsys.readouterr().out)["status"] == "SENT"


def test_mcp_send_uses_env_and_hides_secret(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "load_env", _no_file)
    monkeypatch.setattr(g, "LEDGER", tmp_path / "sent.jsonl")
    monkeypatch.setenv("BRIDGE_PLUGIN_URL", "https://example.invalid/hook")
    monkeypatch.setenv("BRIDGE_PLUGIN_KEY", "secret-key")
    seen = []
    monkeypatch.setattr(g, "post", lambda u, k, b, timeout=30: seen.append((u, k)) or 200)
    reply = g.mcp_handle({
        "jsonrpc": "2.0", "id": 7, "method": "tools/call",
        "params": {"name": "send_task", "arguments": {"job_id": "job-1", "task": "hello"}},
    })
    text = reply["result"]["content"][0]["text"]
    assert reply["result"]["isError"] is False
    assert json.loads(text)["status"] == "SENT"
    assert "secret-key" not in text
    assert "example.invalid" not in text
    assert seen == [("https://example.invalid/hook", "secret-key")]
    assert g.mcp_handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_mcp_missing_options_does_not_read_file(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "load_env", _no_file)
    monkeypatch.setattr(g, "LEDGER", tmp_path / "sent.jsonl")
    monkeypatch.delenv("BRIDGE_PLUGIN_URL", raising=False)
    monkeypatch.delenv("BRIDGE_PLUGIN_KEY", raising=False)
    reply = g.mcp_handle({
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "send_task", "arguments": {"job_id": "job-2", "task": "hello"}},
    })
    assert reply["result"]["isError"] is True
    assert json.loads(reply["result"]["content"][0]["text"])["status"] == "NO_WEBHOOK"


def test_plugin_manifest_user_config_and_icon():
    manifest = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "grok-bot-bridge"
    assert manifest["displayName"] == "Grok Bot Task Inbox"
    assert manifest["version"] == g.PLUGIN_VERSION
    url, key = manifest["userConfig"]["bridge_url"], manifest["userConfig"]["bridge_key"]
    assert url.get("sensitive") is not True
    assert key["sensitive"] is True
    env = manifest["mcpServers"]["grok-bot-bridge"]["env"]
    assert env["BRIDGE_PLUGIN_URL"] == "${user_config.bridge_url}"
    assert env["BRIDGE_PLUGIN_KEY"] == "${user_config.bridge_key}"
    icon = ROOT / manifest["icon"].removeprefix("./")
    data = icon.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n") and data[12:16] == b"IHDR"
    assert struct.unpack(">II", data[16:24]) == (1024, 1024)


def test_plugin_commands_do_not_read_webhook_file_or_pipe_a_download():
    send = (ROOT / "commands" / "send-to-grok-bot.md").read_text(encoding="utf-8")
    results = (ROOT / "commands" / "grok-bot-results.md").read_text(encoding="utf-8")
    for text in (send, results):
        assert "bots.env" not in text
        assert "BRIDGE_URL_" not in text
        assert "BRIDGE_KEY_" not in text
        assert "${user_config." not in text
        lowered = text.lower()
        assert "curl" not in lowered and "wget" not in lowered
        assert "| sh" not in lowered and "| bash" not in lowered
    assert "send_task" in send
    assert "grok_bridge.py send" not in send
    assert "grok_bridge.py\" harvest" in results


def test_listing_readmes_use_absolute_https_links():
    link = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
    for name in ("README.md", "README.zh.md"):
        hrefs = link.findall((ROOT / name).read_text(encoding="utf-8"))
        assert hrefs
        for href in hrefs:
            assert href.startswith("https://"), (name, href)
