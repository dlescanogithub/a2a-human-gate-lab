# Number trace: a2a_human_gate_lab_demo_en.mp4

Every number on screen or in the narration, with its source. Asserted by script (`code/build_trace.py`) at build time against the take recording (`take.json`), the README of the clone (HEAD 8c725da, scratch clone, untouched) and `docs/live/*/summary.json` (copied to `sources/`). Spoken numbers are written in words.

## Offline scenes (fake planner / cassette, no network; badge says so)
| On screen / narration | Value | Where it comes from |
|---|---|---|
| Demo: credit pending `input-required`, self-approval `denied`, approved `completed`, replay `completed`, bank `rejected`, bank replay `rejected`, kill switch `halted`, after kill `failed` | as printed | `python -m a2a_gate demo --evidence var/ev.jsonl 2>/dev/null` (real run in the take, `terminal_dump.txt`) |
| "Applied effects: one" | `applied effects: 1` | same demo output |
| `evidence: valid entries=26` | 26 hash-chained entries | same demo output (fresh `var/`, one run) |
| Evidence rows 9 to 25 (approval_denied self_approval, effect_applied, task_rejected, kill_switch, effect_blocked) | seq, event, reason_code, effect_status | `jq` over `var/ev.jsonl` (`sources/demo_evidence.jsonl`) |
| Edited amount: `line 9 hash mismatch`, `exit=1` | the first non-zero `amount_cents` (12000, line 9, `approval_requested`) set to 1 with `sed` | `python -m a2a_gate verify-evidence var/ev2.jsonl` (`sources/demo_evidence_edited.jsonl`) |
| "Offline, thirty-seven cases pass"; cases 37, passed 37, failed 0 | 37 / 37 / 0 | `python -m a2a_gate.evalkit run` (cassette provider) |
| Forced regression: fail, `exit=1` | gate red | `python -m a2a_gate.evalkit regression` |

## Live measured sample (README table, badge MEASURED 2026-10-18, planner only)
Source: `README.md` lines 73 to 78 and 84 (clone HEAD 8c725da), cross-checked by script against `docs/live/runN/summary.json`:

| run | invariants clean | matched expectations | calls / HTTP | cost | LLM p50 / p95 |
|---|---|---|---|---|---|
| run1 | 37/37 | 35/37 | 35 / HTTP 200 x35 | US$0.00728 | 0.63 / 0.91 s |
| run2 | 37/37 | 35/37 | 35 / HTTP 200 x35 | US$0.00620 | 0.62 / 0.78 s |
| run3 | 37/37 | 34/37 | 35 / HTTP 200 x35 | US$0.00644 | 0.61 / 0.82 s |
| probe | 37/37 | 35/37 | 35 / HTTP 200 x35 | US$0.01057 | 0.67 / 0.84 s |

| Narration | Value | Source |
|---|---|---|
| "Three runs and a probe: invariants clean, thirty-seven of thirty-seven, every time" | 37/37 in all four | table above |
| "Expected outcomes matched thirty-five on run one. Strictly, thirty-four." | run1 35/37; strict count 34/37 | README table; README line 80 ("Strict counts from each results.json are 34/37 (run1) ...") |
| On-screen safety line | 0 unauthorized actions executed, 0 actions without approval, 0 duplicate effects; the model never obeyed the injection | README line 84 |
| Caveats (planner only, scripted approvals, one model, one prompt, three runs, good sign not proof) | text | README lines 69 and 88, shown on screen |

## Closing slide
| Item | Value | Source |
|---|---|---|
| Phases 0 to 4, status implemented / design only | text | docs/SCOPE.md |
| Not covered list | text | README "Not covered yet" paragraph and docs/SCOPE.md out-of-scope |
| ROI [EST]: 40 notes/week, 16 min saved, 10.7 h/week (narrated "about eleven hours") | 40 x 16 / 60 = 10.67 | docs/BUSINESS_CASE.md, tagged [EST], an estimate and not a measured result |

## Caveat not in the video
README live numbers come from a scratch client run on main f64b760; the README itself says they were not repeated with the rewritten in-repo client. A later native two-pass re-run (`the native-client measurement bundle`, main 6a2934b) gave the same 37/37 and 35/37, but it is not shown in the video.
