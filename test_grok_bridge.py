import base64, json
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
    assert g.harvest(ledger=led, results=res, reader=lambda: g.local_replies(store)) == []
