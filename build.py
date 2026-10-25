#!/usr/bin/env python3
"""Build the CQRLOG website (cqrlog.ok2cqr.com).

Fills site/index.html.in with the News (changelog) and Download sections and
writes the result to dist/. The data comes from GitHub:

  * published releases of ok2cqr/cqrlog (drafts and prereleases are skipped):
    the newest one is the current version, its assets are the downloads
  * CHANGELOG at the tag of the newest release: the items of the last
    NEWS_VERSIONS versions

For offline work both sources can be local files:

  python3 build.py --changelog ../cqrlog/CHANGELOG --releases releases.json

Only the Python standard library is used.
"""

import argparse
import html
import json
import os
import re
import shutil
import sys
import urllib.request

REPO = 'ok2cqr/cqrlog'
API = 'https://api.github.com/repos/' + REPO
RELEASES_PAGE = 'https://github.com/' + REPO + '/releases'
NEWS_VERSIONS = 4

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, 'site')

# Download rows in page order. Each row has one main file and optional
# alternatives (other architectures), matched by regex on the asset name.
DOWNLOADS = [
    {'name': 'Ubuntu 26.04+', 'note': '.deb, Qt6',
     'files': [('amd64', r'^cqrlog_.*_amd64\.deb$')]},
    {'name': 'Fedora 44', 'note': '.rpm, Qt6',
     'files': [('x86_64', r'^cqrlog-.*\.x86_64\.rpm$'),
               ('aarch64', r'^cqrlog-.*\.aarch64\.rpm$')]},
    {'name': 'Flatpak', 'note': 'any Linux distribution',
     'files': [('x86_64', r'\.flatpak$')]},
    {'name': 'Snap', 'note': 'any Linux distribution',
     'files': [('amd64', r'^cqrlog_.*_amd64\.snap$'),
               ('arm64', r'^cqrlog_.*_arm64\.snap$')]},
    {'name': 'AppImage', 'note': 'older Linux distributions, Qt5',
     'files': [('x86_64', r'-x86_64\.AppImage$')]},
    {'name': 'macOS', 'note': 'signed and notarized .dmg, Apple Silicon',
     'files': [('arm64', r'-macOS\.dmg$')]},
]

# '*' lines (development changes) are left for the full CHANGELOG
KINDS = [('+', 'New'), ('-', 'Fixed')]

# The maintainer's credit is on almost every line; credits of other
# contributors are kept.
OWN_CREDIT = re.compile(r'\s*\(Petr,\s*OK2CQR\)\s*$')
VERSION_LINE = re.compile(r'^(\d+\.\d+\.\d+)\s+\((\d{4}-\d{2}-\d{2})\)\s*$')


def parse_changelog(text):
    """Return [{'version', 'date', 'items': [(kind, text), ...]}], newest first."""
    text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
    versions = []
    cur = None
    for raw in text.splitlines():
        line = raw.strip()
        m = VERSION_LINE.match(line)
        if m:
            cur = {'version': m.group(1), 'date': m.group(2), 'items': []}
            versions.append(cur)
            continue
        if cur is None or len(line) < 2 or line[0] not in '+-*':
            continue
        item = OWN_CREDIT.sub('', line[1:].strip())
        if item:
            cur['items'].append((line[0], item[0].upper() + item[1:]))
    return versions


def version_key(v):
    return tuple(int(x) for x in v.split('.'))


def tag_version(tag):
    m = re.match(r'^v?(\d+\.\d+\.\d+)$', tag or '')
    return m.group(1) if m else None


def published_releases(releases):
    """Published releases with a version tag, newest version first."""
    out = []
    for r in releases:
        if r.get('draft') or r.get('prerelease'):
            continue
        v = tag_version(r.get('tag_name'))
        if v:
            out.append(dict(r, version=v))
    out.sort(key=lambda r: version_key(r['version']), reverse=True)
    return out


def find_asset(releases, pattern):
    """Newest release asset matching pattern -> (version, url) or None.

    A file uploaded later than the rest (the macOS DMG is built locally) or
    missing from one release falls back to the newest release that has it.
    """
    rx = re.compile(pattern)
    for r in releases:
        for a in r.get('assets', []):
            if rx.search(a['name']):
                return r['version'], a['browser_download_url']
    return None


def render_changelog(versions):
    out = []
    for i, v in enumerate(versions):
        out.append('      <details%s>' % (' open' if i == 0 else ''))
        out.append('        <summary><strong>CQRLOG %s</strong> <span>%s</span></summary>'
                   % (esc(v['version']), esc(v['date'])))
        out.append('        <div class="body">')
        for kind, title in KINDS:
            items = [t for k, t in v['items'] if k == kind]
            if not items:
                continue
            out.append('          <p class="kind">%s</p>' % title)
            out.append('          <ul>')
            out.extend('            <li>%s</li>' % esc(t) for t in items)
            out.append('          </ul>')
        out.append('        </div>')
        out.append('      </details>')
    return '\n'.join(out)


def render_downloads(releases, current):
    out = []
    for row in DOWNLOADS:
        found = [(arch, find_asset(releases, rx)) for arch, rx in row['files']]
        main = found[0][1]
        if main:
            version, url = main
            note = row['note']
            if version != current:
                note += ' (version %s)' % version
        else:
            # not in any release yet: send people to the release list
            url, note = RELEASES_PAGE, row['note']
        alts = ['<a href="%s">%s</a>' % (esc(a[1]), esc(arch))
                for arch, a in found[1:] if a]
        out.append('      <div class="dl">')
        out.append('        <span class="what"><strong>%s</strong> <span>– %s</span></span>'
                   % (esc(row['name']), esc(note)))
        if alts:
            out.append('        <span class="alt">also %s</span>' % ', '.join(alts))
        out.append('        <a class="btn" href="%s">Download</a>' % esc(url))
        out.append('      </div>')
    return '\n'.join(out)


def esc(s):
    return html.escape(s, quote=True)


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'cqrlog-website-build'})
    token = os.environ.get('GITHUB_TOKEN')
    if token and url.startswith('https://api.github.com/'):
        req.add_header('Authorization', 'Bearer ' + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode('utf-8')


def build(releases_json, changelog_text, out_dir):
    releases = published_releases(releases_json)
    if not releases:
        sys.exit('no published release found')
    current = releases[0]['version']

    # Only released versions go to News, even when the CHANGELOG used
    # already carries the next one.
    released = {r['version'] for r in releases}
    versions = [v for v in parse_changelog(changelog_text) if v['version'] in released]
    if not versions or versions[0]['version'] != current:
        sys.exit('CHANGELOG has no entry for the current release %s' % current)
    versions = versions[:NEWS_VERSIONS]

    with open(os.path.join(SITE, 'index.html.in'), encoding='utf-8') as f:
        page = f.read()
    values = {
        'version': esc(current),
        'date': esc(versions[0]['date']),
        'changelog': render_changelog(versions),
        'downloads': render_downloads(releases, current),
    }
    page = re.sub(r'\{\{(\w+)\}\}', lambda m: values[m.group(1)], page)

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    shutil.copytree(SITE, out_dir, ignore=shutil.ignore_patterns('*.in'))
    with open(os.path.join(out_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    return current


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--releases', help='releases JSON file instead of the GitHub API')
    ap.add_argument('--changelog', help='CHANGELOG file instead of the one at the release tag')
    ap.add_argument('--out', default=os.path.join(HERE, 'dist'))
    args = ap.parse_args()

    if args.releases:
        with open(args.releases, encoding='utf-8') as f:
            releases = json.load(f)
    else:
        releases = json.loads(fetch(API + '/releases?per_page=30'))

    if args.changelog:
        with open(args.changelog, encoding='utf-8') as f:
            changelog = f.read()
    else:
        published = published_releases(releases)
        if not published:
            sys.exit('no published release found')
        tag = published[0]['tag_name']
        changelog = fetch('https://raw.githubusercontent.com/%s/%s/CHANGELOG' % (REPO, tag))

    current = build(releases, changelog, args.out)
    print('built %s for CQRLOG %s' % (args.out, current))


if __name__ == '__main__':
    main()
