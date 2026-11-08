# Deal Desk

A local listing-comparison workspace: paste JSON or import CSV, group products,
inspect estimated fair-price bands and rank estimated profit. The interface
shares the Apple-inspired design foundation used by Shelf UI Lab: neutral
surfaces, blue actions, rounded controls and short, purposeful transitions.

This is a new standalone experiment. It reuses existing grouping, matching and
cost helpers, with a new import adapter and comparison board. Attribution and
AI assistance are documented in [NOTICE.md](NOTICE.md).

## Run

Use Python 3.10 or newer:

```sh
python -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn server:app --host 127.0.0.1 --port 8762 --workers 1
```

On Windows, activate with `venv\Scripts\activate`. Open http://127.0.0.1:8762.
No Gemini key, browser automation or Chromium installation is needed.
The server does not crawl marketplaces or call an AI provider.

## Quick walkthrough

1. Click **Build deal board** to compare eight fictional example rows.
   They form four provisional product groups.
2. The first row by estimated profit is the RM3,200 camera. With its group's
   RM3,800 median, RM8 default shipping and a 5% resale fee, estimated total cost
   is RM3,398 and estimated profit is RM402.
3. Select the Sony WH-1000XM5 group to focus on those three headphones.
   The RM210 row has a larger calculated profit than the RM320 row, but it
   also shows missing-parts and return-policy warnings.
4. Change **Order by** between profit, asking price and return on cost.
5. Enter an asking-price ceiling and rebuild. Product bands keep their original
   sample; the ceiling only removes rows from the ranked view.
6. Choose **Paste / import CSV**, then import `example-listings.csv`, paste
   comma-separated records, or download the example through the page.
7. Use **Product query** to narrow the input. Leave it blank to compare all products.

## Import format

Required columns:

```csv
title,price,url
Sony WH-1000XM5 headphones,320,https://www.carousell.com.my/p/example-headphones/
```

The URL above illustrates the required shape; it is not verified stock.

Recommended: `product`, an explicit product label such as `Sony WH-1000XM5`.
Optional: `id, marketplace, description, condition, shipping_cost_myr, seller_rating`.

- Use UTF-8 CSV, up to 30 listing rows and 150,000 text characters.
  The browser file picker also applies a 200 KB size ceiling.
- Prices and shipping are RM amounts without currency symbols.
- The standard CSV parser supports quoted commas, multiline cells and a UTF-8 BOM.
- Missing IDs are assigned by row. Marketplace is inferred from a supported
  product URL if omitted.
- URLs must satisfy the retained marketplace schema: Carousell Malaysia,
  Shopee Malaysia, Lazada Malaysia, Mudah, supported eBay domains or Etsy.
- Duplicate marketplace/ID pairs, bad fields and non-finite prices are set aside
  with reasons. Invalid CSV structure stops the import with an explanatory error.
- Unknown input fields do not establish provenance. A supplied
  `source_verified=true` is reset to false.

The JSON route accepts the same listing fields in an array. JSON and CSV use the
same board-building function, so calculation rules do not drift between formats.

## Grouping and price bands

An explicit `product` label creates an initial bucket. Without it, common
alphanumeric model tokens help keep products such as WH-1000XM4 and WH-1000XM5
apart. The retained grouping helper then separates variants inside each bucket.

Grouping remains provisional. Incomplete titles, seller wording, product
condition and unsupported categories can still lead to unsuitable comparisons.
Product labels supplied by a user are not independently checked.

The UI calls these **estimated fair-price bands**, with the asking-price basis
shown beside them. They are not appraisals or completed-sale valuations:

- Four or more asks: the middle 50% of asking prices.
- Two or three asks: the observed minimum and maximum.
- One ask: the retained helper's ±10% illustrative range, labelled explicitly.

The default resale scenario is the group's asking-price median, calculated before
the budget ceiling. It includes the listing being analysed and may mix product
conditions. Small or biased samples can therefore produce poor estimates.

A manual estimate is also available. It applies to every row in the comparison,
so filter to one product when their resale values differ.

## Profit calculation and ranking

The retained cost engine calculates:

```text
estimated total = asking price + shipping + (resale scenario × resale fee rate)
estimated profit = resale scenario − estimated total
return on cost = estimated profit / estimated total × 100
```

The defaults are RM8 shipping and a 5% resale fee; current settings appear in the
interface. Imported shipping overrides the default. International rows with
unknown delivery/import charges show a minimum-total warning.

Rows are ranked by estimated profit, including negative results. Ranking does not
adjust the profit for risk and does not make a buy recommendation. Description
warnings remain visible beside the figures. Imported records stay unverified.

## Routes

| Route | Purpose |
| --- | --- |
| `GET /` | Apple-inspired Deal Desk interface |
| `GET /api/health` | Local service readiness |
| `GET /api/sample` | Fictional JSON/CSV examples and cost assumptions |
| `GET /api/sample.csv` | Download the example CSV |
| `POST /api/compare` | Build the board from JSON listing records |
| `POST /api/import-csv` | Parse CSV and build the same board |
| `GET /docs` | Interactive API documentation |

## File guide

| File | Responsibility |
| --- | --- |
| `server.py` | New import validation, product buckets, board assembly and routes |
| `sample_data.py` | Eight fictional input records |
| `example-listings.csv` | Runnable CSV example |
| `static/index.html` | Import form, group cards and ranked-results board |
| `static/compare.js` | File reading, input formats, board rendering and sorting |
| `static/apple-ui.css` | Same UI foundation as the frontend study |
| `static/deal-desk.css` | Workspace layout using that design system |
| `static/select-menu.js` | Shared keyboard-friendly dropdown component |
| `schemas.py` | Retained listing schema and supported URL shapes |
| `intelligence.py` | Retained product profiles, grouping and asking-price bands |
| `filters.py`, `search_intent.py` | Retained local matching helpers |
| `agents/context_analyst.py` | Retained description checks |
| `agents/lead_strategist.py` | Retained cost/risk calculations, invoked with AI disabled |

The full application uses provenance checks before live recommendations.
Deal Desk is an imported-data calculator: it applies local matching and cost
helpers without claiming that imported rows passed live source verification.
The reused modules themselves remain unchanged.

## Checks and limits

```sh
python -B -m unittest test_server -v
node --check static/compare.js
```

Twelve tests cover CSV quoting/BOM/multiline cells, malformed input, duplicate
records, product separation, group IDs, calculations, ranking, stable price bands
and unverified provenance. Provider-client creation is blocked during these tests.

The app has no accounts, durable storage or production authentication. CSV files
are read in the browser, then submitted to this local server for comparison.
This app does not intentionally persist them or send them to a provider. Keep it
on localhost; public deployment would require additional access and request controls.

No Apple assets, official components or copied Apple source are included.
See [NOTICE.md](NOTICE.md) and `REUSE_MANIFEST.json` for the origin of reused code.

