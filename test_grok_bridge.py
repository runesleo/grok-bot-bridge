import base64, json, sys
import grok_bridge as g

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
