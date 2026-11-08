import csv
from io import StringIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from server import app
from sample_data import sample_records


class DealDeskTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        blocker = patch('google.genai.Client', side_effect=AssertionError('Deal Desk must not call a provider'))
        blocker.start()
        self.addCleanup(blocker.stop)

    def payload(self, **changes):
        return {'query': '', 'resale_estimate': None, 'max_price': None,
                'listings': sample_records(), **changes}

    def post(self, **changes):
        response = self.client.post('/api/compare', json=self.payload(**changes))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def csv_text(self, rows):
        output = StringIO(newline='')
        columns = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    def test_home_and_examples_are_local(self):
        self.assertIn('Deal Desk', self.client.get('/').text)
        self.assertTrue(self.client.get('/api/sample').json()['synthetic'])
        download = self.client.get('/api/sample.csv')
        self.assertEqual(download.status_code, 200)
        self.assertIn('text/csv', download.headers['content-type'])

    def test_default_board_groups_products_and_ranks_profit(self):
        body = self.post()
        self.assertEqual((body['submitted'], body['retained'], body['rejected']), (8, 8, 0))
        self.assertEqual(len(body['groups']), 4)
        self.assertEqual(body['offers'][0]['id'], '6')
        self.assertEqual(body['offers'][0]['profit'], 402)
        self.assertEqual(body['offers'][0]['resale_estimate'], 3800)
        profits = [row['profit'] for row in body['offers']]
        self.assertEqual(profits, sorted(profits, reverse=True))
        self.assertEqual(body['provider_attempts'], 0)

    def test_query_budget_manual_costs_and_condition_warning(self):
        body = self.post(query='Sony WH-1000XM5 headphones', max_price=400, resale_estimate=450)
        self.assertEqual((body['retained'], body['rejected']), (2, 6))
        rows = {row['id']: row for row in body['offers']}
        self.assertEqual(rows['1']['total_cost'], 350.5)
        self.assertEqual(rows['1']['profit'], 99.5)
        self.assertEqual(rows['1']['estimate_basis'], 'manual')
        self.assertEqual(body['offers'][0]['id'], '5')
        self.assertTrue(rows['5']['review_flags'])
        self.assertFalse(rows['1']['source_verified'])

    def test_budget_does_not_change_the_price_sample(self):
        whole = self.post()
        limited = self.post(max_price=300)
        bands = {group['id']: group['asking_price_band'] for group in whole['groups']}
        self.assertEqual(bands, {group['id']: group['asking_price_band'] for group in limited['groups']})
        self.assertTrue(all(row['price'] <= 300 for row in limited['offers']))

    def test_csv_handles_bom_quoted_commas_and_newlines(self):
        rows = sample_records()[:2]
        rows[0]['description'] = 'Used, tested.\nIncludes the case.'
        content = '\ufeff' + self.csv_text(rows)
        response = self.client.post('/api/import-csv', json={'csv_text': content})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['retained'], 2)

    def test_minimal_csv_infers_marketplace_and_assigns_ids(self):
        row = sample_records()[0]
        minimal = {key: row[key] for key in ['title', 'price', 'url']}
        response = self.client.post('/api/import-csv', json={'csv_text': self.csv_text([minimal])})
        self.assertEqual(response.status_code, 200)
        item = response.json()['offers'][0]
        self.assertEqual(item['marketplace'], 'carousell')
        self.assertEqual(item['id'], 'row-1')
        self.assertFalse(item['source_verified'])

    def test_import_cannot_claim_verified_provenance(self):
        rows = sample_records()[:1]
        rows[0]['source_verified'] = True
        rows[0]['source'] = 'carousell_live'
        body = self.post(listings=rows)
        self.assertFalse(body['offers'][0]['source_verified'])

    def test_duplicate_invalid_and_nonfinite_values_are_set_aside(self):
        rows = sample_records()
        rows += [rows[0].copy(), {'id': 'bad'},
                 {**rows[0], 'id': 'bad-price', 'price': 'Infinity'}]
        body = self.post(listings=rows)
        self.assertEqual(body['retained'], 8)
        self.assertEqual(body['rejected'], 3)

    def test_model_tokens_separate_products_without_manual_labels(self):
        rows = [sample_records()[0], sample_records()[2]]
        for row in rows:
            row.pop('product')
        body = self.post(listings=rows)
        self.assertEqual(len(body['groups']), 2)

    def test_explicit_product_labels_have_unique_group_ids(self):
        row = sample_records()[0]
        rows = [{**row, 'product': 'Product A'}, {**row, 'id': 'second', 'product': 'Product B'}]
        body = self.post(listings=rows, query='Sony WH-1000XM5 headphones')
        self.assertEqual(len({group['id'] for group in body['groups']}), 2)

    def test_bad_csv_headers_shape_and_row_limit_return_errors(self):
        for content in [
            'name,price\nExample,10',
            'title,price,url,url\nExample,10,x,x',
            'title,price,url\nExample,10,x,extra',
            self.csv_text([sample_records()[0]] * 31),
        ]:
            response = self.client.post('/api/import-csv', json={'csv_text': content})
            self.assertEqual(response.status_code, 400, response.text)

    def test_empty_rows_and_invalid_settings_are_rejected(self):
        self.assertEqual(self.client.post('/api/compare', json=self.payload(listings=[])).status_code, 422)
        self.assertEqual(self.client.post('/api/compare', json=self.payload(resale_estimate=-1)).status_code, 422)
        self.assertEqual(self.client.post('/api/import-csv', json={'csv_text': 'title,price,url\n'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()

