# GitHub Pages

Public studio: https://tomaslin.github.io/MuseVideoWorkflow/

`.github/workflows/pages.yml` builds `_site/` with
`python3 scripts/build-studio.py --out _site`, then configures Pages, uploads
that directory and deploys it. It runs on main pushes and manual dispatch.
The artifact contains a real project catalog and verified committed final
videos, as well as both cutting room and storyboard views. Copying only
`apps/studio/` is insufficient: it does not contain the project catalog.

Pages must use **GitHub Actions** as its publishing source. The workflow attempts
to enable Pages automatically. If GitHub denies site creation, an administrator
must select Settings → Pages → Source → GitHub Actions, then rerun the workflow.
The source setting requires administration capability; ordinary Contents write
permission alone does not provide it. A successful code push is not a successful
deployment: confirm the workflow and the public URL before claiming it is live.

Raw clips are local ignored work files. Commit the verified final with
`scripts/checkin-final.sh <slug>` to include it in the next cloud build. Do not
use LFS pointers for web media. See `docs/local-video.md` for the intake/edit/redo
flow and local preview commands.
