"""Tests for build.py: python3 -m unittest test_build"""

import os
import tempfile
import unittest

import build

CHANGELOG = """<!-- comment
3.9.9 (2000-01-01)
  + not a version, inside the comment
-->

3.3.0 (2026-10-23)
  + one shared RBN connection (Petr, OK2CQR)
  - grayline shadow fixed (Petr, OK2CQR)
  + GTK3 support (Saku, OH1KH)
  * tests in src/rbn (Petr, OK2CQR)

3.2.1 (2026-10-06)
  - Debian package paths <fixed> (Petr, OK2CQR)

3.2.0 (2026-09-25)
  + faster club import (Petr, OK2CQR)

3.1.0 (2026-09-12)
  + version check (Petr, OK2CQR)

3.0.0 (2026-08-15)
  + macOS support (Petr, OK2CQR)
"""


def release(tag, assets, draft=False):
    return {'tag_name': tag, 'draft': draft, 'prerelease': False,
            'assets': [{'name': a, 'browser_download_url': 'https://dl/%s/%s' % (tag, a)}
                       for a in assets]}


class ParseChangelog(unittest.TestCase):
    def test_versions_items_and_credits(self):
        vs = build.parse_changelog(CHANGELOG)
        self.assertEqual([v['version'] for v in vs], ['3.3.0', '3.2.1', '3.2.0', '3.1.0', '3.0.0'])
        self.assertEqual(vs[0]['date'], '2026-10-23')
        self.assertEqual(vs[0]['items'], [
            ('+', 'One shared RBN connection'),
            ('-', 'Grayline shadow fixed'),
            ('+', 'GTK3 support (Saku, OH1KH)'),
            ('*', 'Tests in src/rbn'),
        ])

    def test_real_changelog_parses(self):
        path = os.path.join(build.HERE, '..', 'cqrlog', 'CHANGELOG')
        if not os.path.exists(path):
            self.skipTest('cqrlog checkout not next to the website')
        with open(path, encoding='utf-8') as f:
            vs = build.parse_changelog(f.read())
        self.assertGreater(len(vs), 10)
        self.assertTrue(all(v['items'] for v in vs[:NEWS]))


NEWS = build.NEWS_VERSIONS


class Releases(unittest.TestCase):
    def test_drafts_skipped_and_sorted_by_version(self):
        rs = build.published_releases([
            release('v3.10.0', [], draft=True),
            release('v3.2.0', []),
            release('v3.2.1', []),
            release('nightly', []),
        ])
        self.assertEqual([r['version'] for r in rs], ['3.2.1', '3.2.0'])

    def test_asset_falls_back_to_older_release(self):
        rs = build.published_releases([
            release('v3.3.0', ['cqrlog_3.3.0-1_amd64.deb']),
            release('v3.2.1', ['cqrlog_3.2.1-1_amd64.deb', 'CQRLOG-3.2.1-macOS.dmg']),
        ])
        self.assertEqual(build.find_asset(rs, r'-macOS\.dmg$'),
                         ('3.2.1', 'https://dl/v3.2.1/CQRLOG-3.2.1-macOS.dmg'))
        self.assertIsNone(build.find_asset(rs, r'\.rpm$'))


class Build(unittest.TestCase):
    def test_page(self):
        releases = [
            release('v3.3.0', ['cqrlog_3.3.0-1_amd64.deb', 'cqrlog-3.3.0-1.fc44.x86_64.rpm']),
            release('v3.2.1', ['CQRLOG-3.2.1-macOS.dmg']),
            release('v3.2.0', []), release('v3.1.0', []), release('v3.0.0', []),
            release('v3.4.0', [], draft=True),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, 'dist')
            self.assertEqual(build.build(releases, CHANGELOG, out), '3.3.0')
            with open(os.path.join(out, 'index.html'), encoding='utf-8') as f:
                page = f.read()
            self.assertTrue(os.path.exists(os.path.join(out, 'assets', 'cqrlog-darkmode.png')))
            self.assertFalse(os.path.exists(os.path.join(out, 'index.html.in')))
        self.assertNotIn('{{', page)
        self.assertIn('Version 3.3.0, released 2026-10-23', page)
        self.assertIn('<details open>\n        <summary><strong>CQRLOG 3.3.0</strong>', page)
        self.assertEqual(page.count('<details'), NEWS)
        self.assertNotIn('CQRLOG 3.0.0', page)
        self.assertIn('Debian package paths &lt;fixed&gt;', page)
        self.assertIn('https://dl/v3.3.0/cqrlog-3.3.0-1.fc44.x86_64.rpm', page)
        self.assertIn('Apple Silicon (version 3.2.1)', page)
        # Flatpak is in no release: the button goes to the release list
        self.assertIn('<a class="btn" href="%s">' % build.RELEASES_PAGE, page)

    def test_unreleased_changelog_entry_is_not_shown(self):
        releases = [release('v3.2.1', []), release('v3.2.0', [])]
        with tempfile.TemporaryDirectory() as tmp:
            build.build(releases, CHANGELOG, os.path.join(tmp, 'dist'))
            with open(os.path.join(tmp, 'dist', 'index.html'), encoding='utf-8') as f:
                page = f.read()
        self.assertNotIn('CQRLOG 3.3.0', page)
        self.assertIn('Version 3.2.1', page)


if __name__ == '__main__':
    unittest.main()
