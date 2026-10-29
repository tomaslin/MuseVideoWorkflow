# Variants, alternate realities, and history

## Variants

A variant is a full alternate reality of a project, not an edit that
destroys the original.

- Every project starts as `v1`.
- Any change via prompt ("make it rainier", "change the ending",
  "warmer palette") creates a new variant: `v2`, `v3`, and so on.
- A variant records: `parentVariant`, `changePrompt`, a new `seed`
  (hash of idea + change prompt + parent seed), and the full artifact
  set at branch time.
- The original is never overwritten. You can ship `v1` while `v3`
  exists, or compare them shot by shot.
- In the studio UI, "Save edit as new variant" and "Branch variant"
  do this in one click. In the repo, a variant is a folder:
  `projects/<slug>/variants/v2/` with its own `project.json`,
  `state.json`, sequences, prompts, and `final/` when shipped.

## History

History is append-only. Every event records: timestamp, action,
detail, state before/after, variant, and — for generation — prompt
hash, model, model version, and clip file.

Events include: project created, brief/treatment/script written,
critique saved, prompt packet built, clip generated, clip critiqued,
clip redone, variant created, audio stem added, assembled, checked
in, verified, shipped, and any waiver (with a reason).

History is never edited to hide a redo, a failed clip, or a waived
critique. A project whose history was rewritten cannot be audited,
and this pipeline refuses to pretend otherwise.

## Auto-advance, no approval gates

In the studio UI, auto-advance is on by default: the state machine
moves through stages without stopping for approval at each gate.
That does not mean gates disappear — it means they are checked
automatically (`validate`, prompt-hash checks, duration math) and
failures are logged as history events, not silently skipped. A human
sign-off is still required for `shipped`, and for any waiver.
This is a pipeline choice, not a way around platform approvals:
GitHub connector writes still ask for approval in chat, because that
approval belongs to the runtime, not to this repo.
