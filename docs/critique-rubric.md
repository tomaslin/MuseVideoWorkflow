# Critique rubric

Every critique is saved in the project under `critiques/`, with the stage,
the finding, the severity, and the fix. Critiques are not chat comments.

## Severity

- **Blocker:** the video cannot ship with this. A broken arc, a missing
  sequence, a locked block violated, a line that changes meaning.
- **Major:** the video is noticeably weaker. A beat with no visual action,
  a sequence with no reversal, every shot the same size, music obscuring
  dialogue.
- **Minor:** polish. A repeated word, a composition that could be stronger,
  a sound cue that could be one precise sound instead of three.

## Script critique (before generation)

1. Is the premise one sentence, and does the ending pay it off?
2. Does every beat change something (power, knowledge, feeling)?
3. Is every beat visual — could it be filmed, or is it only narrated?
4. Is there a reversal, and is it earned rather than announced?
5. Does dialogue reveal, advance, or change — or merely explain?
6. Are negation, numbers, dates, and uncertainty preserved exactly?
7. Is there any placeholder, teaser, or `[TBD]`? Any one is a blocker.

## Shot-plan critique (before generation)

1. Does shot count match duration? (duration_sec / 10, rounded up, per
   the generation unit — and is any shot asked to do more than 10 seconds
   of story?)
2. Does every shot carry its locked look block and its characters' locked
   descriptions verbatim?
3. Is shot size varied across a sequence, or is it all medium shots?
4. Is camera movement varied, and is stillness used on purpose?
5. Does the sequence have an opening image, a turn, and a closing image?
6. Do transitions between sequences have a reason (match cut, sound
   bridge, cross-cut), not just a cut?

## Clip critique (after each batch)

Automated checks: prompt match, locked blocks present, shot number and
sequence correct, file present, duration close to 10 seconds.

Human visual check (you, the reviewer): name outlier shot numbers only.
Muse redoes those shots from the same reference image and locked blocks.
A batch is locked only when its critiques are resolved or you waive them
in `state.json` with a reason.

## Final critique (before shipping)

1. Does the assembled order match the EDL exactly?
2. Does the duration match the shot list within one shot length?
3. Are spoken words above music in the mix?
4. Are captions present and faithful to the audio script?
5. Is the final manifest complete: checksum, resolution, shot order,
   audio stems, review state?
