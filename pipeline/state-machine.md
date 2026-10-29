# Execution state machine

State lives in `projects/<slug>/state.json`. A stage may only start when
its gate is recorded as passed. Muse advances state; it does not skip it.

## States, in order

| State | Gate to leave it |
|---|---|
| `brief` | Brief has premise, mood, duration, audience, language |
| `treatment` | Treatment has arc, opening image, turn, closing image |
| `script` | Script is complete, no placeholders, beats are visual |
| `script-critiqued` | Script critique saved, blockers fixed |
| `look-and-characters` | Look bible versioned, character sheets locked, reference images made |
| `shot-list` | Shot count matches duration, every shot has size/movement/action |
| `shot-list-critiqued` | Shot-plan critique saved, blockers fixed |
| `generating` | Batches recorded in manifest, <=6 clips per batch |
| `clips-critiqued` | Every batch locked, or outliers waived with a reason |
| `audio` | Voice stems, music mood, SFX list, captions drafted |
| `assembled` | Final video written, EDL and manifest written |
| `checked-in` | Final video present in `projects/<slug>/final/` in the repo |
| `verified` | `verify-final` passed: duration, order, checksum |
| `shipped` | Human reviewer (you) confirms the shipped video |

## Rules

- A project may move backward (for example, `clips-critiqued` back to
  `shot-list`) when a critique requires it. The move is recorded with a
  reason; history is not rewritten.
- `shipped` requires `verified`, and `verified` requires `checked-in`.
  No state is marked by assertion — only by a passing check or by your
  explicit waiver, recorded in `state.json`.
- The manifest is append-only in spirit: a redo adds a new clip version
  under the same shot; it does not delete the old attempt's record.
