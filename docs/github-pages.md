# GitHub Pages: visual access to the studio

The studio UI is a static site, so GitHub Pages is the visual remedy:
no server, no install, just a URL you can open and share.

## How it is deployed

`.github/workflows/pages.yml` deploys `apps/studio/` to GitHub Pages
on every push to `main`, using GitHub Actions. The workflow uploads
only the studio folder as the Pages artifact, so the published site
is exactly the UI — index, storyboard view, styles, and script.

## Enabling it (one setting, once the repo exists)

In the repo: Settings → Pages → Build and deployment → Source:
**GitHub Actions**. After the first successful workflow run, the site
is live at:

```
https://<owner>.github.io/MuseVideoWorkflow/
```

For this project, once pushed under `tomaslin`, that is
`https://tomaslin.github.io/MuseVideoWorkflow/` — verify the actual
URL from the workflow run / Pages settings after the first deploy,
and record it in the repo README.

## What you can see there

- The prompt-first pipeline UI (`apps/studio/index.html`): stages,
  artifacts, editing, variants, state machine, history.
- The storyboard view (`apps/studio/storyboard.html`): every shot as
  a visual panel (size, movement, action, sound cue, tension value),
  plus a tension curve drawn from the panels' tension values. This is
  the visual check that the story's tension actually rises and falls
  before any clip is generated.
- The UI stores its working project in the browser's local storage
  and can export/import project JSON. The repo remains the record of
  truth for shipped projects; the Pages site is the visual working
  surface, not a separate database.

## Local preview (before Pages is live)

```bash
cd apps/studio && python3 -m http.server 8000
# open http://localhost:8000/
```

Do not open `index.html` directly from disk if your browser blocks
local scripts; the local server above avoids that.
