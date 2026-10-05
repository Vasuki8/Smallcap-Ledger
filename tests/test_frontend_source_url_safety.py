"""Source links must remain HTTP(S)-only in both core and research UIs."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class FrontendSourceUrlSafetyTests(unittest.TestCase):
    def test_core_source_link_has_explicit_scheme_allowlist(self):
        source=(ROOT/'dist'/'app.js').read_text(encoding='utf-8')
        self.assertIn('function safeSourceURL(url)',source)
        self.assertIn("['https:','http:'].includes(u.protocol)",source)
        self.assertIn('const safe=safeSourceURL(url)',source)

    def test_research_source_link_keeps_its_existing_scheme_allowlist(self):
        source=(ROOT/'dist'/'research.js').read_text(encoding='utf-8')
        self.assertIn('function safeURL(url)',source)
        self.assertIn("['https:', 'http:'].includes(u.protocol)",source)


if __name__=='__main__':
    unittest.main()
