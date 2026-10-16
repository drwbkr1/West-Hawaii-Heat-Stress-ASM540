import csv
import json
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import unquote

import crw_downloader as core
import crw_regional as region


class RegionalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'fixture.csv'
        self.start, self.end = date(2015,9,1), date(2015,9,2)
        for attr, values in [('LATITUDES', (Decimal('20.325'),Decimal('20.275'))),
                             ('LONGITUDES',(Decimal('-156.125'),Decimal('-156.075')))]:
            p = patch.object(region,attr,values)
            p.start()
            self.addCleanup(p.stop)
        self.args = SimpleNamespace(attempts=2,timeout=10,backoff=0)

    def rows(self):
        return [region.HEADER,region.UNITS]+[
            [d+'T12:00:00Z',str(lat),str(lon),'27.4','4.2','0']
            for d in region.dates(self.start,self.end)
            for lat in region.LATITUDES for lon in region.LONGITUDES]

    def write(self,rows,path=None):
        with (path or self.path).open('w',newline='',encoding='utf-8') as stream:
            csv.writer(stream).writerows(rows)

    def check(self,rows):
        self.write(rows)
        return region.validate_csv(self.path,self.start,self.end)

    def fetch(self,url,path,timeout):
        self.write(self.rows(),path)
        return {'final_url':url}

    def test_exact_cell_calendar_and_land(self):
        rows = self.rows()
        rows[2][3:] = ['NaN','NaN','1']
        rows[3][3:] = ['-327.68','-327.68','2']
        result = self.check(rows)
        self.assertTrue(result['valid'],result)
        self.assertEqual(result['rows'],8)
        self.assertEqual(result['mask_counts'],{'1':1,'2':1,'0':6})
        self.assertEqual(result['missing_values']['CRW_DHW'],2)
        self.assertEqual(sum(result['valid_dhw_days_by_cell'].values()),6)

    def test_missing_or_duplicate_cannot_pass(self):
        self.assertFalse(self.check(self.rows()[:-1])['valid'])
        rows = self.rows()
        rows[-1] = rows[-2].copy()
        result = self.check(rows)
        self.assertFalse(result['valid'])
        self.assertEqual(result['duplicate_cell_days'],1)
        self.assertEqual(result['missing_cell_days'],1)

    def test_wrong_grid_time_values_mask_units(self):
        for col,value in [(0,'2015-09-01T00:00:00Z'),(1,'20.326'),(2,'-155'),
                          (3,'inf'),(4,'-1'),(5,'3'),(5,'0.5')]:
            rows = self.rows()
            rows[2][col] = value
            self.assertFalse(self.check(rows)['valid'],(col,value))
        rows = self.rows()
        rows[1] = rows[1].copy()
        rows[1][3] = 'Kelvin'
        self.assertFalse(self.check(rows)['valid'])

    def test_html_rejected(self):
        self.path.write_text('<html>upstream failure</html>')
        self.assertFalse(region.validate_csv(self.path,self.start,self.end)['valid'])

    def test_url_scope_and_year_plan(self):
        url=unquote(region.build_url(self.start,self.end))
        for variable in region.VARIABLES:
            self.assertIn(variable+'[(2015-09-01T12:00:00Z)',url)
        self.assertIn('[(20.325):1:(20.275)][(-156.125):1:(-156.075)]',url)
        plan=region.jobs(SimpleNamespace(sample=False))
        self.assertEqual(len(plan),24)
        self.assertEqual(sum((e-s).days+1 for _,s,e in plan),730)

    def test_retry_retains_partial_and_resume_no_network(self):
        calls=0
        def flaky(url,path,timeout):
            nonlocal calls
            calls+=1
            if calls==1:
                path.write_bytes(b'interrupted')
                raise URLError('disconnect')
            return self.fetch(url,path,timeout)
        with patch.object(core,'fetch',side_effect=flaky),patch.object(core.time,'sleep'):
            first=region.transfer(self.root,'fixture',self.start,self.end,self.args)
        self.assertEqual(first['state'],'promoted')
        self.assertEqual(len(list(self.root.rglob('*.part'))),1)
        with patch.object(core,'fetch',side_effect=AssertionError('network forbidden')):
            second=region.transfer(self.root,'fixture',self.start,self.end,self.args,first)
        self.assertEqual(first['checksum'],second['checksum'])
        self.assertEqual((self.root/first['destination']).stat().st_size,first['bytes'])

    def test_tampered_existing_never_reacquired_or_overwritten(self):
        with patch.object(core,'fetch',side_effect=self.fetch):
            first=region.transfer(self.root,'fixture',self.start,self.end,self.args)
        path=self.root/first['destination']
        content=path.read_text().replace('27.4','27.5')
        path.write_text(content)
        with patch.object(core,'fetch',side_effect=AssertionError('network forbidden')):
            with self.assertRaisesRegex(ValueError,'changed'):
                region.transfer(self.root,'fixture',self.start,self.end,self.args,first)
        self.assertEqual(path.read_text(),content)

    def test_untracked_collision_is_preserved(self):
        dest=self.root/'2015'/'crw_west_hawaii_fixture.csv'
        dest.parent.mkdir()
        dest.write_text('untracked')
        with self.assertRaisesRegex(ValueError,'collision'):
            region.transfer(self.root,'fixture',self.start,self.end,self.args)
        self.assertEqual(dest.read_text(),'untracked')

    def test_verify_only_missing_manifest_no_network(self):
        with patch.object(core,'fetch',side_effect=AssertionError('network forbidden')):
            with self.assertRaisesRegex(ValueError,'no regional manifest'):
                region.main(['--output',str(self.root),'--verify-only'])
        self.assertFalse((self.root/'.download.lock').exists())

    def test_reject_legacy_manifest_and_keep_active_lock(self):
        (self.root/'manifest.json').write_text(json.dumps({'schema_version':1}))
        with self.assertRaisesRegex(ValueError,'incompatible manifest'):
            region.main(['--output',str(self.root)])
        lock=self.root/'.download.lock'
        lock.write_text('active owner')
        with self.assertRaises(FileExistsError):
            region.main(['--output',str(self.root)])
        self.assertEqual(lock.read_text(),'active owner')

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError,'unsafe'):
            region.safe_path(self.root,'../outside.csv')


if __name__=='__main__':
    unittest.main()
