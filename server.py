"""Deal Desk: imported listings, provisional product groups and cost previews."""
import csv
from hashlib import sha256
from io import StringIO
import math
from pathlib import Path
import re
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

import config
from agents.context_analyst import _deterministic
from agents.lead_strategist import decide
from filters import _terms, _is_relevant
from intelligence import group_listings, identity_reason, price_band
from search_intent import plan_search
from schemas import Listing, VisionCheck
from sample_data import sample_records

ROOT = Path(__file__).resolve().parent
app = FastAPI(title='Deal Desk', description='Compare imported records locally. No crawling or AI calls.')
MAX_ROWS = 30
CSV_FIELDS = ['id', 'product', 'title', 'price', 'url', 'marketplace',
              'description', 'condition', 'shipping_cost_myr', 'seller_rating']


def cost_assumptions():
    return {'default_shipping_myr': config.SHIPPING_COST_MYR,
            'resale_fee_rate': config.PLATFORM_FEE_PCT}


class CompareRequest(BaseModel):
    query: str = Field(default='', max_length=120)
    resale_estimate: float | None = Field(default=None, gt=0, le=1_000_000)
    max_price: float | None = Field(default=None, gt=0, le=1_000_000)
    listings: list[dict] = Field(min_length=1, max_length=MAX_ROWS)


class CSVRequest(BaseModel):
    csv_text: str = Field(min_length=1, max_length=150_000)
    query: str = Field(default='', max_length=120)
    resale_estimate: float | None = Field(default=None, gt=0, le=1_000_000)
    max_price: float | None = Field(default=None, gt=0, le=1_000_000)


def sample_csv():
    output = StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(sample_records())
    return output.getvalue()


def read_csv(value: str) -> list[dict]:
    """Use the standard CSV parser: quoted commas and multiline cells are valid."""
    reader = csv.DictReader(StringIO(value.lstrip('\ufeff'), newline=''), strict=True)
    try:
        headers = [str(name).strip().lower().replace(' ', '_') for name in (reader.fieldnames or [])]
        if len(headers) != len(set(headers)):
            raise ValueError('CSV column names must be unique.')
        if not {'title', 'price', 'url'}.issubset(headers):
            raise ValueError('CSV needs title, price and url columns. Product is optional but recommended.')
        reader.fieldnames = headers
        rows = []
        for number, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f'CSV row {number} has a different number of cells from the header.')
            if not any(value.strip() for value in row.values()):
                continue
            rows.append({key: value.strip() for key, value in row.items() if value.strip()})
            if len(rows) > MAX_ROWS:
                raise ValueError(f'Import at most {MAX_ROWS} listings at a time.')
        if not rows:
            raise ValueError('The CSV has no listing rows.')
        return rows
    except csv.Error as error:
        raise ValueError(f'Could not read the CSV: {error}') from error


def marketplace_from_url(url: str) -> str:
    host = (urlsplit(url).hostname or '').lower()
    for domain, marketplace in [
        ('carousell.com.my', 'carousell'), ('shopee.com.my', 'shopee'),
        ('lazada.com.my', 'lazada'), ('mudah.my', 'mudah'),
        ('ebay.com', 'ebay'), ('ebay.co.uk', 'ebay'),
        ('ebay.com.au', 'ebay'), ('ebay.com.sg', 'ebay'), ('etsy.com', 'etsy'),
    ]:
        if host in {domain, 'www.' + domain}:
            return marketplace
    raise ValueError('Use a supported marketplace product URL.')


def product_bucket(raw: dict, item: Listing) -> tuple[str, str | None]:
    """An explicit product label takes priority; model tokens keep common variants apart."""
    label = str(raw.get('product') or '').strip()
    if len(label) > 120:
        raise ValueError('Product labels must be at most 120 characters.')
    if label:
        return 'label:' + ' '.join(label.casefold().split()), label
    # This is an import adapter, not a universal product-recognition model.
    models = re.findall(r'\b(?=[a-z0-9-]*[a-z])(?=[a-z0-9-]*\d)[a-z0-9]+(?:-[a-z0-9]+)*\b',
                        item.title.casefold())
    return ('models:' + '|'.join(sorted(set(models))) if models else 'general'), None


def build_board(request: CompareRequest):
    valid, rejected, buckets = [], [], {}
    seen = set()
    query = request.query.strip()
    intent = plan_search(query, use_ai=False) if query else None
    query_words = _terms(query)
    for index, raw in enumerate(request.listings):
        try:
            data = {key: value for key, value in raw.items() if value is not None and value != ''}
            data.setdefault('id', f'row-{index + 1}')
            data.setdefault('marketplace', marketplace_from_url(str(data.get('url', ''))))
            # Imported claims cannot establish provenance. No live verification occurs here.
            data['source'] = 'demo_cache'
            data['source_verified'] = False
            item = Listing.model_validate(data)
            if not item.title.strip():
                raise ValueError('A listing needs a non-blank title.')
            if not math.isfinite(item.price) or item.price > 1_000_000:
                raise ValueError('Asking price must be finite and no more than RM1,000,000.')
            if item.shipping_cost_myr is not None and (
                not math.isfinite(item.shipping_cost_myr) or item.shipping_cost_myr > 1_000_000
            ):
                raise ValueError('Shipping must be finite and no more than RM1,000,000.')
            identity = (item.marketplace, item.id)
            if identity in seen:
                raise ValueError('Duplicate marketplace and listing ID.')
            seen.add(identity)
            if query:
                mismatch = identity_reason(item.title, query, item.description)
                if mismatch:
                    raise ValueError(mismatch)
                if not _is_relevant(item, query_words, intent):
                    raise ValueError('Not relevant to the product query.')
            key, label = product_bucket(raw, item)
            buckets.setdefault(key, {'label': label, 'listings': []})['listings'].append(item)
            valid.append(item)
        except (ValidationError, ValueError, TypeError) as error:
            reason = error.errors(include_input=False)[0]['msg'] if isinstance(error, ValidationError) else str(error)
            rejected.append({'id': str(raw.get('id') or f'row-{index + 1}'),
                             'title': str(raw.get('title') or 'Invalid record')[:300], 'reason': reason})

    # Group before applying the purchase ceiling. The price sample stays stable.
    groups, offers = [], []
    for bucket_key, bucket in buckets.items():
        for group in group_listings(bucket['listings'], query or bucket_key):
            band = price_band([item.price for item in group.listings])
            estimate = request.resale_estimate if request.resale_estimate is not None else band['estimate']
            group_name = bucket['label'] or group.name
            group_id = sha256(f'{bucket_key}|{group.group_id}'.encode()).hexdigest()[:12]
            displayed = 0
            for item in group.listings:
                if request.max_price is not None and item.price > request.max_price:
                    rejected.append({'id': item.id, 'title': item.title,
                                     'reason': f'Asking price exceeds RM{request.max_price:,.2f}.'})
                    continue
                analysis = _deterministic(item)
                vision = VisionCheck(consistency_score=None, images_checked=0)
                decision = decide(item, analysis, vision, estimate, use_ai=False)
                flags = list(dict.fromkeys(analysis.flaws_found + analysis.missing_parts + analysis.red_flags))
                if not item.landed_cost_verified:
                    flags.append('International shipping/import charges are unverified; total may be a minimum.')
                offers.append({
                    'id': item.id, 'marketplace': item.marketplace, 'url': item.url,
                    'title': item.title, 'condition': item.condition,
                    'product_group': group_name, 'group_id': group_id, 'price': item.price,
                    'resale_estimate': estimate, 'total_cost': decision.total_cost_myr,
                    'profit': decision.estimated_profit_myr, 'margin_pct': decision.estimated_margin_pct,
                    'estimate_basis': 'manual' if request.resale_estimate is not None else 'group_asking_median',
                    'review_flags': flags, 'source_verified': False,
                    'landed_cost_verified': item.landed_cost_verified,
                })
                displayed += 1
            groups.append({
                'id': group_id, 'name': group_name, 'kind': group.profile.kind,
                'variant': group.profile.label, 'warning': group.profile.warning,
                'asking_price_band': band, 'resale_estimate': estimate,
                'sample_count': len(group.listings), 'visible_count': displayed,
                'band_method': 'interquartile_asking_range' if len(group.listings) >= 4
                    else 'observed_asking_range' if len(group.listings) > 1
                    else 'single_ask_plus_minus_10_percent',
            })

    offers.sort(key=lambda item: (-item['profit'], item['price'], item['marketplace'], item['id']))
    for rank, item in enumerate(offers, 1):
        item['rank'] = rank
    return {
        'submitted': len(request.listings), 'retained': len(offers), 'rejected': len(rejected),
        'groups': groups, 'offers': offers, 'discarded': rejected, 'provider_attempts': 0,
        'valuation_mode': 'manual' if request.resale_estimate is not None else 'group_asking_median',
        'cost_assumptions': cost_assumptions(),
        'notice': 'Imported records only. Price bands use supplied asking prices, not completed sales. Profit is a scenario, not a buying recommendation.',
    }


@app.get('/api/health')
def health():
    return {'ok': True, 'mode': 'local_import_analysis', 'live_requests_enabled': False}


@app.get('/api/sample')
def sample():
    return {'synthetic': True, 'listings': sample_records(), 'csv': sample_csv(),
            'cost_assumptions': cost_assumptions()}


@app.get('/api/sample.csv')
def download_sample():
    return Response(sample_csv(), media_type='text/csv',
                    headers={'Content-Disposition': 'attachment; filename="deal-desk-example.csv"'})


@app.post('/api/compare')
def compare(request: CompareRequest):
    return build_board(request)


@app.post('/api/import-csv')
def import_csv(request: CSVRequest):
    try:
        rows = read_csv(request.csv_text)
    except ValueError as error:
        raise HTTPException(400, detail={'message': str(error)}) from error
    return build_board(CompareRequest(query=request.query, max_price=request.max_price,
                                     resale_estimate=request.resale_estimate, listings=rows))


app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


@app.get('/')
def home():
    return FileResponse(ROOT / 'static/index.html')

