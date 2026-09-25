"""Research-desk presentation regressions. No network, database, or new dependency.

Browser interaction QA is documented separately in docs/UI-HANDOFF.md.
These checks run against the same client source that Pages publishes.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist' if (ROOT / 'dist').is_dir() else ROOT / 'site'


class ResearchUIAssets(unittest.TestCase):
    def test_dependency_order_and_cache_revision(self):
        class Tags(HTMLParser):
            scripts = []
            styles = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == 'script': self.scripts.append(attrs)
                if tag == 'link' and attrs.get('rel') == 'stylesheet': self.styles.append(attrs)
        tags = Tags()
        tags.feed((DIST / 'index.html').read_text(encoding='utf-8'))
        paths = [item.get('src', '').split('?')[0] for item in tags.scripts]
        self.assertEqual(paths, ['./runtime-config.js', './analytics.js', './static-data.js', './app.js', './research.js'])
        self.assertIn('defer', tags.scripts[-1])
        self.assertIn('defer', tags.scripts[-2])
        self.assertEqual(len(tags.styles), 1)
        self.assertIn('?v=', tags.styles[0]['href'])
        self.assertIn('?v=', tags.scripts[-1]['src'])

    @unittest.skipUnless(shutil.which('node'), 'Node is needed for client syntax checks')
    def test_client_syntax(self):
        for name in ('research.js', 'app.js', 'analytics.js', 'static-data.js'):
            with self.subTest(asset=name):
                subprocess.run(['node', '--check', str(DIST / name)], check=True, capture_output=True, text=True)


@unittest.skipUnless(shutil.which('node'), 'Node is needed for UI helper tests')
class ResearchUIHelpers(unittest.TestCase):
    def evaluate(self, expression):
        script = """
const fs = require('node:fs'), vm = require('node:vm');
const context = {window: {}, URL};
vm.runInNewContext(fs.readFileSync(process.argv[1], 'utf8'), context);
const api = context.window.LedgerResearch;
process.stdout.write(JSON.stringify((EXPRESSION)));
""".replace('EXPRESSION', expression)
        result = subprocess.run(['node', '-e', script, str(DIST / 'research.js')], check=True, capture_output=True, text=True)
        return json.loads(result.stdout)

    def test_saved_plan_identifiers_are_validated_and_deduplicated(self):
        self.assertEqual(self.evaluate("api.codes([118778,'118778','120',0,-1,1.5,true,null,{},'abc','9007199254740992'])"), [118778,120])
        self.assertEqual(self.evaluate('api.codes({})'), [])

    def test_missing_invalid_and_boolean_numbers_stay_unavailable(self):
        self.assertEqual(self.evaluate("[null,undefined,'', ' ',false,{},[],Infinity,NaN].map(api.number)"), [None]*9)
        self.assertEqual(self.evaluate("[0,'0',-4.25,'0.68'].map(api.number)"), [0,0,-4.25,0.68])

    def test_only_http_source_links_are_allowed(self):
        self.assertEqual(self.evaluate("['javascript:alert(1)','data:text/html,test','file:///tmp/test','/relative',''].map(api.safeURL)"), ['']*5)
        self.assertEqual(self.evaluate("api.safeURL('https://example.com/report?month=8')"), 'https://example.com/report?month=8')

    def test_null_return_values_sort_last_in_both_directions(self):
        rows = "[{code:1,family:'A',returns:{'5':null}},{code:2,family:'B',returns:{'5':10}},{code:3,family:'C',returns:{'5':-3}},{code:4,family:'D',returns:{'5':0}}]"
        self.assertEqual(self.evaluate(f"api.sortFunds({rows},'5','desc').map(x=>x.code)"), [2,4,3,1])
        self.assertEqual(self.evaluate(f"api.sortFunds({rows},'5','asc').map(x=>x.code)"), [3,4,2,1])

    def test_aum_sort_is_numeric_and_does_not_mutate_input(self):
        self.assertEqual(self.evaluate("(()=>{const rows=[{code:1,family:'A',metrics:{aum:{value:'9'}}},{code:2,family:'B',metrics:{aum:{value:'80'}}}];const sorted=api.sortFunds(rows,'aum');return [rows.map(x=>x.code),sorted.map(x=>x.code)];})()"), [[1,2],[2,1]])

    def test_expense_sort_keeps_core_fee_priority(self):
        rows = "[{code:1,family:'A',metrics:{ter:{value:.8},base_expense_ratio:{value:.1}}},{code:2,family:'B',metrics:{expense_ratio:{value:.6}}},{code:3,family:'C',metrics:{}}]"
        self.assertEqual(self.evaluate(f"api.sortFunds({rows},'ter','asc').map(x=>x.code)"), [2,1,3])

    def test_inactive_and_unknown_sources_are_not_healthy(self):
        self.assertEqual(self.evaluate("[{enabled:0,status:'Checked'},{enabled:1,status:'Checked'},{enabled:1,status:'Partial'},{enabled:1,status:'New status'},{enabled:true,status:'Excluded'}].map(api.sourceState)"), ['inactive','checked','attention','pending','inactive'])

    def test_fund_name_sort_has_deterministic_code_tie_break(self):
        rows = "[{code:3,family:'Zulu'},{code:2,family:'Alpha'},{code:1,family:'Alpha'}]"
        self.assertEqual(self.evaluate(f"api.sortFunds({rows},'family','asc').map(x=>x.code)"), [1,2,3])


if __name__ == '__main__':
    unittest.main()
