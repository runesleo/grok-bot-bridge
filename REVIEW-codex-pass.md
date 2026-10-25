# Independent review — v0.1.0 (Codex, read-only, 2026-10-25)

Reviewer was asked to evaluate from scratch, without a prior analysis to copy.

## 🔴 Blockers — all fixed

| Finding | Fix |
|---|---|
| A job recorded as `UNKNOWN` (timeout) could be sent again on a second run, so the Bot might do it twice. | `send` now treats `SENT` and `UNKNOWN` as already sent; only a refused send may go again. Test added. |
| An unchecked job id was used as a file name, so `harvest` could write outside `results/`. | Job ids must match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$`, checked in `send` and `harvest`. Test added. |
| The setup prompt claimed the worst case is a wasted read-only task; the side-effect ban is only an instruction to the Bot. | Wording changed in both setup prompts and both READMEs: it lowers the risk, it is not a hard limit; don't give a task-inbox Bot posting, wallet or account tools. |
| Docs never created `~/.grok-bridge/`, so a clean first run failed. | Setup now runs `mkdir -p … && touch … && chmod 600 …`; a missing config prints what to create. |

## 🟡 Warnings

| Finding | Status |
|---|---|
| Any 2xx other than 200 was recorded as failed. | Fixed: any 2xx is `SENT`. |
| Message parsing required compact JSON. | Fixed: whitespace around `:` accepted; test fixture now uses spaced JSON. |
| Plain `http://` webhook URLs would send the key in clear text. | Fixed: refused with `NOT_HTTPS`. Test added. |
| `GROK_BRIDGE_HOME` also moves the config file; docs didn't say. | Fixed in both READMEs. |
| No `cd` after `git clone`. | Fixed in READMEs and install.md. |
| `harvest` silently returned nothing when the desktop app data is missing. | Fixed: exits 2 with a message. |
| "Answers come back by themselves" overstated; `harvest` must be run. | Fixed: "with one command". |
| `harvest` matches by job id across all local chats, not per Bot. | Documented under Known limitations; use unique ids. |
| Key file permissions are not checked by the script. | Left as is; setup creates the file with `chmod 600`. |

## Re-verified after fixes

`python3 -m pytest -q test_grok_bridge.py` — 2 passed (offline). Live: one send, one duplicate blocked locally, reply collected about a minute later.
