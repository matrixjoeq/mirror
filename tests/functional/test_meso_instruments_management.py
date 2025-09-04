import json
import unittest

from app import app as flask_app


class TestMesoInstrumentsManagement(unittest.TestCase):
    def setUp(self):
        self.app = flask_app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_add_list_delete_instrument(self):
        # upsert one instrument
        resp = self.client.post('/api/meso/instruments', data={
            'symbol': 'TEST.XY',
            'name': 'Test Instrument',
            'market': 'CN',
            'asset_class': 'equity',
            'currency': 'CNY',
            'provider': 'EASTMONEY',
            'instrument_type': 'INDEX',
            'is_active': '1'
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])

        # list should contain it
        resp = self.client.get('/api/meso/instruments')
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()
        self.assertTrue(payload['success'])
        items = payload['data'].get('all') or []
        syms = {r.get('symbol') for r in items}
        self.assertIn('TEST.XY', syms)

        # refresh incrementally (should not error)
        resp = self.client.post('/api/meso/refresh?symbols=TEST.XY')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

        # delete the symbol data only
        resp = self.client.post('/api/meso/delete_symbol?symbol=TEST.XY&remove_meta=0')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])
        # delete metadata as well
        resp = self.client.post('/api/meso/delete_symbol?symbol=TEST.XY&remove_meta=1')
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])
        # after remove_meta, list should NOT contain the symbol
        resp = self.client.get('/api/meso/instruments')
        self.assertEqual(resp.status_code, 200)
        items = (resp.get_json() or {}).get('data', {}).get('all') or []
        syms = {r.get('symbol') for r in items}
        self.assertNotIn('TEST.XY', syms)

    def test_invalid_provider_and_type_validation(self):
        # invalid provider
        r = self.client.post('/api/meso/instruments', data={
            'symbol': 'BAD.XY', 'market': 'US', 'asset_class': 'equity', 'currency': 'USD',
            'provider': 'BADPROV', 'instrument_type': 'INDEX'
        })
        self.assertEqual(r.status_code, 400)
        # invalid instrument_type
        r = self.client.post('/api/meso/instruments', data={
            'symbol': 'BAD2.XY', 'market': 'US', 'asset_class': 'equity', 'currency': 'USD',
            'provider': 'YAHOO', 'instrument_type': 'BADTYPE'
        })
        self.assertEqual(r.status_code, 400)


if __name__ == '__main__':
    unittest.main()


