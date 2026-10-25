# cqrlog.ok2cqr.com

One-page website of CQRLOG. `site/index.html.in` is the page; `build.py`
fills in the News and Download sections from the GitHub releases of
[ok2cqr/cqrlog](https://github.com/ok2cqr/cqrlog) and writes `dist/`.

```bash
python3 build.py                       # live data from GitHub
python3 -m http.server -d dist 8000    # preview
python3 -m unittest test_build         # tests
```

Offline / before a release (the CHANGELOG from a local checkout):

```bash
python3 build.py --changelog ../cqrlog/CHANGELOG --releases releases.json
```

## What updates by itself

- **Version and date** (hero, Download): the newest published, non-draft
  release; the date comes from its CHANGELOG entry.
- **News**: the last 4 released versions from the CHANGELOG at the newest
  release tag, `+` lines as New, `-` as Fixed. `*` lines (development) are
  left out, so is the "(Petr, OK2CQR)" credit; other contributors are kept.
- **Download**: asset links matched by name (`DOWNLOADS` in `build.py`). A file
  missing from the newest release (the DMG uploaded later) links to the newest
  release that has it, with "(version X)"; a file in no release goes to the
  release list.

`.github/workflows/pages.yml` rebuilds every 3 hours, on push and by hand, and
deploys to GitHub Pages only when the page changed.

## Setup (once)

1. Push this directory as a GitHub repository `ok2cqr/cqrlog.ok2cqr.com`.
2. Settings → Pages → Source: **GitHub Actions**; custom domain
   `cqrlog.ok2cqr.com`, Enforce HTTPS.
3. DNS: `cqrlog.ok2cqr.com CNAME ok2cqr.github.io.` (replaces the current A record).
4. Optional, for an update right after publishing a release instead of within
   3 hours: a fine-grained token with Contents read/write on this repository,
   stored as `WEBSITE_DISPATCH_TOKEN` in ok2cqr/cqrlog, and this workflow there:

   ```yaml
   on:
     release:
       types: [ published ]
   jobs:
     website:
       runs-on: ubuntu-latest
       steps:
         - run: gh api repos/ok2cqr/cqrlog.ok2cqr.com/dispatches -f event_type=cqrlog-release
           env:
             GH_TOKEN: ${{ secrets.WEBSITE_DISPATCH_TOKEN }}
   ```

## Editing

Text sections (About, Features, FAQ, Contact) are plain HTML in
`site/index.html.in`. A new package type is one line in `DOWNLOADS`.
Design reference: the design handoff (not in the repository).
