#!/usr/bin/env python3
"""nginx behind Traefik keeps the client's https in its redirects.

TLS ends at Traefik, so an nginx in a stack sees plain http. A relative
`return 301 /path` is sent as an absolute Location with the scheme nginx sees
unless `absolute_redirect off` is set: Nextcloud's /.well-known/caldav and
carddav answered `http://…` on the step 8 lab host, and a DAV client following
them left TLS. These tests hold the setting in place wherever a shipped nginx
config redirects relatively, and keep Nextcloud's DAV discovery relative.

Run:
    python3 scripts/ci/test_nginx_redirects.py
    python3 -m unittest discover -s scripts/ci -p 'test_*.py'
"""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
NEXTCLOUD = REPO / "apps" / "nextcloud" / "nginx" / "nginx.conf"
RELATIVE_REDIRECT = re.compile(r"^\s*(?:location\b.*\{\s*)?return\s+30[1278]\s+/", re.M)


def nginx_configs():
    for path in REPO.rglob("*.conf"):
        if "node_modules" in path.parts or ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(r"^\s*server\s*\{", text, re.M):
            yield path, text


class NginxRedirects(unittest.TestCase):
    def test_relative_redirects_stay_relative(self):
        for path, text in nginx_configs():
            if RELATIVE_REDIRECT.search(text):
                with self.subTest(config=str(path.relative_to(REPO))):
                    self.assertRegex(text, re.compile(r"^\s*absolute_redirect\s+off\s*;", re.M))

    def test_nextcloud_dav_discovery_is_relative(self):
        text = NEXTCLOUD.read_text(encoding="utf-8")
        for name in ("caldav", "carddav"):
            with self.subTest(name=name):
                line = re.search(rf"location\s*=\s*/\.well-known/{name}\s*\{{([^}}]*)\}}", text)
                self.assertIsNotNone(line, f"/.well-known/{name} is not handled")
                self.assertRegex(line.group(1), r"return\s+301\s+/remote\.php/dav/\s*;")

    def test_no_redirect_names_a_scheme(self):
        for path, text in nginx_configs():
            with self.subTest(config=str(path.relative_to(REPO))):
                self.assertNotRegex(text, r"return\s+30[1278]\s+(?:http://|\$scheme://)")


if __name__ == "__main__":
    unittest.main()
