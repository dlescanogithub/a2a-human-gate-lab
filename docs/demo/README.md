# Demo recording

[a2a_human_gate_lab_demo_en.mp4](a2a_human_gate_lab_demo_en.mp4) is a screen recording of a real local run of this repository. The narration voice is synthetic xAI text-to-speech.

Subtitles: [English](a2a_human_gate_lab_demo_en.en.srt). The script that was spoken is [final_script.md](final_script.md). The video file still carries the original Spanish soft subtitle track and was not re-encoded.

## What the video shows

The terminal scenes run this repo's commands with the fake planner. The number trace marks those scenes offline.

- `python -m a2a_gate demo`: a credit note stays `input-required`, self-approval is denied, a second person approves, a replay does not apply a second effect, a supplier bank change is rejected and stays rejected, then the kill switch blocks the next effect. The run prints one applied effect and `evidence: valid entries=26`.
- The hash-chained log for that run, then one amount edited after the fact. `python -m a2a_gate verify-evidence` fails at that line and exits 1.
- `python -m a2a_gate.evalkit run`: 37 cassette cases pass. `python -m a2a_gate.evalkit regression` fails the gate (`risky effect without approval`, exit 1).
- The live table on screen is the earlier scratch-client measurement already published in the README (three runs and a probe, 2026-10-18). The narration says invariants were clean, thirty-seven of thirty-seven, and that expected outcomes matched thirty-five on run one, strictly thirty-four. Those figures were quoted from the published logs. The recording spend file records no live planner calls.
- The closing slide: work past the lab is design only. The ROI line is tagged [EST] (about eleven hours a week). It is an estimate.

The take, the evidence files, and the sources the numbers were checked against are in [evidence_a2a_human_gate_lab_demo/](evidence_a2a_human_gate_lab_demo/).

## Where each number comes from

[number_trace.md](evidence_a2a_human_gate_lab_demo/number_trace.md) maps each number in the video to its source: the demo output, the cassette eval, the README live table, or the [EST] business-case line.

## What this recording is

Planner only on the live sample. Approvals were scripted. One model, one prompt. The voice is synthetic. The video shows the scratch-client table. A two-pass measurement with the in-repo client is in [docs/live/native_v2/](../live/native_v2/). Clean invariants on that small sample are a good sign, not a proof.

Voice and transcription spend for the recording is in [spend.md](evidence_a2a_human_gate_lab_demo/spend.md).
