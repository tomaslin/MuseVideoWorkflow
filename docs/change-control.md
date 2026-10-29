# Change control & picture lock

## Picture lock

Picture lock is a state, not a feeling. A cut is picture-locked when:

- The EDL is frozen and recorded in `final/edl.json`.
- Every shot is a locked clip, or a waived outlier with a reason.
- The state is `assembled` moving to `checked-in`, and the lock is
  recorded in `state.json` with a timestamp and the EDL hash.

## After lock

After picture lock, a story change (reorder, replace, add, or cut a
shot) is a **change request**, recorded in `critiques/change-requests.md`
with: what changes, why, cost in batches/clips, schedule impact, and
what must be redone (audio, color, captions, QC). The change is only
applied after the request is approved in the project (by you, in chat
or in the studio UI), and the EDL hash changes with it.

Audio, color, captions, and QC are never silently re-run after a lock
change. They are re-run and re-recorded, or the project is not
`verified`.

## Variants vs. changes

A variant (see `docs/variants-and-history.md`) is an alternate reality
branched before lock, or a new branch from a locked cut. A change
request mutates a locked cut in place. Variants are cheap to explore;
changes after lock are expensive by design, and the pipeline prices
them that way.
