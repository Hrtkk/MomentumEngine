# Independent ET preliminary scan — 7 October 2026

Output: `et_top100_2026-10-07.csv`, **100 data rows** (plus header), ranked by ET one-day percentage gain descending within its Nifty 500 universe. No NSE bhavcopy or Claude pipeline data was used to populate the CSV.

**Price qualification:** `close` contains ET’s post-session `lastTradedPrice` / quote `current`, not a separately certified NSE official closing-auction/bhavcopy close. All 100 quote prices and percentage changes agree with the screener. This is a preliminary ET cross-check; compare this distinction when reconciling with bhavcopy.

**RSI qualification:** `rsi14` is blank for all 100 rows. ET exposes `currentRsi` (label “RSI Current”) for all 100, but the retrieved screener metadata does not specify the lookback period. A 14-session lookback was not assumed. The exact ET values are preserved as `et_currentRsi` in `et_row_audit.json` and in `api_technicals.html` (JSON response).

## Session, ranking and coverage

- ET snapshot `unixDateTime`: 1791369127000 = **2026-10-07T16:02:07+05:30**. Both overview and technical responses have this timestamp; the retrieved stock quotes are all dated 7 October 2026, after the regular-session close.
- Individual NSE quote timestamps range from 2026-10-07 15:50:01.0 to 2026-10-07 16:00:24.0 IST.
- Live page `selectedFilter` explicitly identifies `Nifty 500`, `indexId=2371`, `exchange=nse`; request uses `filterType=index`, `filterValue=[2371]`, `apiType=gainers`, `duration=1D`.
- Page 1 contains 100 gainers; page 2 contains 49. All 149 are unique and non-increasing by percentage gain. The first 100 are retained in ET’s original order, including tie order. Each selected stock’s individual quote metadata also has `nifty500=true`.
- Rank 100: SANSERA, 0.69%; rank 101: USHAMARTEQ, 0.69%.
- SMA above/below-20 screens returned 138 + 359 = 497 unique stocks; together they cover all selected 100. The top-100 Technicals view also covers all 100. SMA20 and SMA50 agree between these sources.

## Fields and missing values

Numeric values use ET’s `filterFormatValue`, not its rounded display `value`. Currency is INR; `pct_change` is percentage points (14.7 means +14.7%); volume is shares, not turnover.

| CSV field | ET field / treatment | Missing rows |
|---|---|---:|
| rank | 1–100 in ET gainers order | 0 |
| symbol | assetSymbol with terminal EQ or BE series suffix removed | 0 |
| name | assetName | 0 |
| close | lastTradedPrice (post-close price proxy; see qualification above) | 0 |
| pct_change | percentChange | 0 |
| volume | volume from gainers overview | 0 |
| sma20 | currentSma20 | 0 |
| sma50 | currentSma50 | 0 |
| sma200 | currentSma200 from above/below-SMA20 screens | 0 |
| rsi14 | Blank: currentRsi exists, but 14-period definition not verified | 100 |
| high52w | company.nse.fiftyTwoWeekHighPrice | 0 |
| low52w | company.nse.fiftyTwoWeekLowPrice | 0 |
| source_url | Fetched individual ET stock quote URL; common screener/API sources below | 0 |

## Reference inspection and data-quality limitations

- Inspected `momentum-engine/reference/gainers_technical_scan_2026-10-06.html` and `gainers_momentum_2026-10-07.html` read-only. They are generated reports, not raw ET pages. They name ET market stats / technical screeners, but contain no exact market-stats or screener URL; only per-stock ET company links. The first report embeds 100 rows; the second embeds 100 previous-day and 100 current-day rows.
- Reference fields include symbol/name/company URL, price, daily change, RSI, relative distance to SMAs and 52-week high, returns, support/risk and derived scores/signals. The 6 October report includes hi52 and d50; the 7 October report does not contain raw volume, SMA20/50/200 or both raw 52-week extrema. No values were copied or reverse-engineered from these reports.
- The 6 October reference explicitly describes previous-day technical indicators combined with intraday prices. The live technical responses have a 7 October snapshot timestamp but no per-indicator price-as-of date. Do not interpret that response timestamp as proof the SMAs/RSI incorporate the 7 October close. A technical-detail probe for CHENNPETRO returned `currentDto.priceDate` = 6 October 2026 for its pivot/ATR/Heikin-Ashi data, even though its update timestamp is on 7 October. This establishes lag in that endpoint, not the exact vintage of every screener indicator.
- ET symbols contain series suffixes. EQ was removed for 98 stocks and BE for HFCL and MTARTECH. The raw identifiers are retained in `et_row_audit.json`. For a bhavcopy join, use the corresponding EQ/BE series; do not silently omit BE stocks.
- The initially probed legacy URL used indexid=2370; it returned HTTP 200 but did not identify Nifty 500 and was not used for the output. The live page establishes 2371 as the correct ET index ID.
- Some rendered prices are rounded to integers, while the embedded raw field retains decimals. The CSV preserves raw field precision. No prices, indicators, or percentage changes were recomputed, imputed, or copied from the reference reports.
- 29 quote pages have volume differences from the gainers overview. The overview is retained consistently for every CSV volume. Both values are recorded below. Price and percentage-change discrepancies between these two ET sources: 0/100.
- 52-week highs/lows come from NSE quote data only. Corporate-action adjustment methodology and official closing-price equivalence were not independently established.
- All attempted HTTP requests returned 200; no access block occurred. HTTP success alone was not treated as evidence of correct content. Parsed stock IDs, dates, universe flags, row counts and sorting were validated.

| Symbol | Gainers overview volume (CSV) | Individual NSE quote volume |
|---|---:|---:|
| BHARTIHEXA | 1512589 | 1512590 |
| MAHABANK | 20883267 | 20883266 |
| BELRISE | 3749664 | 3749658 |
| HFCL | 12439455 | 12439454 |
| PNBHOUSING | 1125058 | 1125048 |
| JUBLFOOD | 2597754 | 2597729 |
| PNB | 18275848 | 18275770 |
| GILLETTE | 26580 | 26579 |
| CPPLUS | 208910 | 208895 |
| BALRAMCHIN | 1646549 | 1646445 |
| ADANIGREEN | 6420423 | 6420216 |
| ASAHIINDIA | 142786 | 142757 |
| FORTIS | 1858360 | 1858057 |
| TARIL | 3041176 | 3041174 |
| ASTRAL | 759824 | 759815 |
| BSE | 6608257 | 6608157 |
| DMART | 406908 | 406904 |
| APOLLOTYRE | 546102 | 546001 |
| SUPREMEIND | 381975 | 381972 |
| BHARTIARTL | 13920833 | 13920832 |
| SHYAMMETL | 514924 | 514923 |
| AVANTIFEED | 237908 | 237907 |
| ENRIN | 426581 | 426551 |
| BANKINDIA | 9853574 | 9853569 |
| AFCONS | 230744 | 230633 |
| CDSL | 1021744 | 1021756 |
| CENTRALBK | 3892597 | 3892497 |
| BANKBARODA | 6320157 | 6319957 |
| SWIGGY | 16172713 | 16172705 |

## Working endpoints and request bodies

Public data endpoints were discovered from JavaScript referenced by the live ET pages. Requests used Python 3 standard-library `urllib.request`, with a browser User-Agent. No authenticated session or subscription credentials were used.

- Page: https://economictimes.indiatimes.com/stocks/marketstats/top-gainers
- Technical page: https://economictimes.indiatimes.com/stocks/marketstats-technicals/ltp-above-sma-20
- `POST https://etapi.indiatimes.com/et-screener/v2/intraday-stats`: overview `viewId=6925`; Technicals `viewId=6918`.
- `POST https://etapi.indiatimes.com/et-screener/v2/technical-data`: `viewId=6986`, `firstOperand=lastTradedPrice`, `secondOperand=currentSma20`, `operationType=Above` or `Below`, Nifty 500 filter, `pagesize=500`.

Exact POST bodies (all are read-only data queries):

### api_gainers.html
URL: https://etapi.indiatimes.com/et-screener/v2/intraday-stats
Retrieved: 2026-10-07T21:07:37.263124+05:30; HTTP 200.
```json
{
  "viewId": 6925,
  "apiType": "gainers",
  "duration": "1D",
  "filterValue": [
    2371
  ],
  "filterType": "index",
  "sort": [],
  "pagesize": 100,
  "pageno": 1
}
```

### api_technicals.html
URL: https://etapi.indiatimes.com/et-screener/v2/intraday-stats
Retrieved: 2026-10-07T21:07:37.263764+05:30; HTTP 200.
```json
{
  "viewId": 6918,
  "apiType": "gainers",
  "duration": "1D",
  "filterValue": [
    2371
  ],
  "filterType": "index",
  "sort": [],
  "pagesize": 100,
  "pageno": 1
}
```

### api_sma.html
URL: https://etapi.indiatimes.com/et-screener/v2/technical-data
Retrieved: 2026-10-07T21:07:37.264149+05:30; HTTP 200.
```json
{
  "viewId": 6986,
  "firstOperand": "lastTradedPrice",
  "operationType": "Above",
  "secondOperand": "currentSma20",
  "filterValue": [
    2371
  ],
  "filterType": "index",
  "sort": [],
  "pagesize": 500,
  "pageno": 1
}
```

### api_sma_below.html
URL: https://etapi.indiatimes.com/et-screener/v2/technical-data
Retrieved: 2026-10-07T21:07:56.498801+05:30; HTTP 200.
```json
{
  "base64Decode": false,
  "countOnly": false,
  "pageno": 1,
  "pagesize": 500,
  "deviceId": "app",
  "screenerId": null,
  "viewId": 6986,
  "filterType": "index",
  "filterValue": [
    "2371"
  ],
  "sort": [],
  "filterList": null,
  "queryCondition": null,
  "sortBy": null,
  "collectionId": 0,
  "apiType": null,
  "duration": null,
  "timespan": null,
  "firstOperand": "lastTradedPrice",
  "operationType": "Below",
  "secondOperand": "currentSma20",
  "sectorId": null
}
```

### api_gainers_page2.html
URL: https://etapi.indiatimes.com/et-screener/v2/intraday-stats
Retrieved: 2026-10-07T21:09:37.649390+05:30; HTTP 200.
```json
{
  "base64Decode": false,
  "countOnly": false,
  "pageno": 2,
  "pagesize": 100,
  "deviceId": "app",
  "screenerId": null,
  "viewId": 6925,
  "filterType": "index",
  "filterValue": [
    "2371"
  ],
  "sort": [],
  "filterList": null,
  "queryCondition": null,
  "sortBy": null,
  "collectionId": 0,
  "apiType": "gainers",
  "duration": "1D",
  "timespan": null,
  "firstOperand": null,
  "operationType": null,
  "secondOperand": null,
  "sectorId": null
}
```

## Complete retrieval ledger (IST)

Timestamps below record request start in IST (+05:30). Exact response headers, request bodies and raw response filenames are in `et_retrieval_log.json`. Raw `.html` files for API calls contain JSON, despite the filename extension. Saved responses support reproducibility because these live URLs will change in later sessions.

| Retrieval timestamp IST | HTTP | Exact URL | Saved response |
|---|---:|---|---|
| 2026-10-07T21:05:02.793889+05:30 | 200 | https://economictimes.indiatimes.com/marketstats/pid-1314,exchange-nse,sortorder-desc,sortby-percentchange,indexid-2370.cms | et_probe_0.html |
| 2026-10-07T21:05:02.794916+05:30 | 200 | https://economictimes.indiatimes.com/markets/stocks/stock-screener | et_probe_1.html |
| 2026-10-07T21:05:02.795225+05:30 | 200 | https://economictimes.indiatimes.com/trent-ltd/stocks/companyid-13456.cms | et_probe_2.html |
| 2026-10-07T21:05:40.917356+05:30 | 200 | https://economictimes.indiatimes.com/stocks/marketstats/top-gainers | gainers.html |
| 2026-10-07T21:05:40.918079+05:30 | 200 | https://economictimes.indiatimes.com/stocks/marketstats-technicals/ltp-above-sma-20 | sma.html |
| 2026-10-07T21:05:40.918423+05:30 | 200 | https://economictimes.indiatimes.com/js_marketstats/v-287,minify-1.cms | marketjs.html |
| 2026-10-07T21:06:41.496823+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/3027-7733341f90e31f5d.js | chunk_0.html |
| 2026-10-07T21:06:41.497561+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/9532-63bb87e894d1e76c.js | chunk_1.html |
| 2026-10-07T21:06:41.497826+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/9389-6d67be4430c66ae6.js | chunk_2.html |
| 2026-10-07T21:06:41.498134+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/app/stocks/marketstats/%5B%5B...slug%5D%5D/page-2e7dd335349afa59.js | chunk_3.html |
| 2026-10-07T21:07:08.512033+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/9064-6bd19fa75855c25b.js | lib_0.html |
| 2026-10-07T21:07:08.512643+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/9467-c1520959b8ee7078.js | lib_1.html |
| 2026-10-07T21:07:08.513111+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/8667-b17ed26c7e507e06.js | lib_2.html |
| 2026-10-07T21:07:08.513972+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/5503-3cd1477237ed7f43.js | lib_3.html |
| 2026-10-07T21:07:08.514306+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/8848-7797f2ee770e1785.js | lib_4.html |
| 2026-10-07T21:07:08.691120+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/8708-b25f33cd8f6821d4.js | lib_5.html |
| 2026-10-07T21:07:08.709879+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/5700-10bd0f8e718df1ff.js | lib_6.html |
| 2026-10-07T21:07:08.728753+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/6405-61d334426c078d95.js | lib_7.html |
| 2026-10-07T21:07:08.736543+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/6349-9b014e85f66f20ff.js | lib_8.html |
| 2026-10-07T21:07:08.755736+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/7782-0bd01ff1373be818.js | lib_9.html |
| 2026-10-07T21:07:08.858325+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/602dbae6-c58260fc3478a4a8.js | lib_10.html |
| 2026-10-07T21:07:08.873437+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/4186-22fd187cf5ade646.js | lib_11.html |
| 2026-10-07T21:07:08.910812+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/6926-38cd274e5b960690.js | lib_12.html |
| 2026-10-07T21:07:37.263124+05:30 | 200 | https://etapi.indiatimes.com/et-screener/v2/intraday-stats | api_gainers.html |
| 2026-10-07T21:07:37.263764+05:30 | 200 | https://etapi.indiatimes.com/et-screener/v2/intraday-stats | api_technicals.html |
| 2026-10-07T21:07:37.264149+05:30 | 200 | https://etapi.indiatimes.com/et-screener/v2/technical-data | api_sma.html |
| 2026-10-07T21:07:56.498801+05:30 | 200 | https://etapi.indiatimes.com/et-screener/v2/technical-data | api_sma_below.html |
| 2026-10-07T21:07:57.037527+05:30 | 200 | https://economictimes.indiatimes.com/chennai-petroleum-corporation-ltd/stocks/companyid-11661.cms | quote_11661.html |
| 2026-10-07T21:07:57.037716+05:30 | 200 | https://economictimes.indiatimes.com/pvr-inox-ltd/stocks/companyid-16320.cms | quote_16320.html |
| 2026-10-07T21:07:57.037845+05:30 | 200 | https://economictimes.indiatimes.com/ptc-industries-ltd/stocks/companyid-7565.cms | quote_7565.html |
| 2026-10-07T21:07:57.058936+05:30 | 200 | https://economictimes.indiatimes.com/bharti-hexacom-ltd/stocks/companyid-18654.cms | quote_18654.html |
| 2026-10-07T21:07:57.059683+05:30 | 200 | https://economictimes.indiatimes.com/cupid-ltd/stocks/companyid-7772.cms | quote_7772.html |
| 2026-10-07T21:07:57.589849+05:30 | 200 | https://economictimes.indiatimes.com/physicswallah-ltd/stocks/companyid-2282824.cms | quote_2282824.html |
| 2026-10-07T21:07:57.683386+05:30 | 200 | https://economictimes.indiatimes.com/black-box-ltd/stocks/companyid-12930.cms | quote_12930.html |
| 2026-10-07T21:07:57.736310+05:30 | 200 | https://economictimes.indiatimes.com/gland-pharma-ltd/stocks/companyid-1996493.cms | quote_1996493.html |
| 2026-10-07T21:07:57.754459+05:30 | 200 | https://economictimes.indiatimes.com/mangalore-refinery-and-petrochemicals-ltd/stocks/companyid-11391.cms | quote_11391.html |
| 2026-10-07T21:07:57.896887+05:30 | 200 | https://economictimes.indiatimes.com/aegis-logistics-ltd/stocks/companyid-23.cms | quote_23.html |
| 2026-10-07T21:07:58.149008+05:30 | 200 | https://economictimes.indiatimes.com/bank-of-maharashtra/stocks/companyid-12283.cms | quote_12283.html |
| 2026-10-07T21:07:58.231813+05:30 | 200 | https://economictimes.indiatimes.com/belrise-industries-ltd/stocks/companyid-2239238.cms | quote_2239238.html |
| 2026-10-07T21:07:58.255494+05:30 | 200 | https://economictimes.indiatimes.com/kalyan-jewellers-india-ltd/stocks/companyid-2002614.cms | quote_2002614.html |
| 2026-10-07T21:07:58.287368+05:30 | 200 | https://economictimes.indiatimes.com/syrma-sgs-technology-ltd/stocks/companyid-2077325.cms | quote_2077325.html |
| 2026-10-07T21:07:58.717891+05:30 | 200 | https://economictimes.indiatimes.com/indraprastha-gas-ltd/stocks/companyid-751.cms | quote_751.html |
| 2026-10-07T21:07:58.766954+05:30 | 200 | https://economictimes.indiatimes.com/hfcl-ltd/stocks/companyid-13649.cms | quote_13649.html |
| 2026-10-07T21:07:58.798431+05:30 | 200 | https://economictimes.indiatimes.com/emmvee-photovoltaic-power-ltd/stocks/companyid-2270215.cms | quote_2270215.html |
| 2026-10-07T21:07:59.011206+05:30 | 200 | https://economictimes.indiatimes.com/pine-labs-ltd/stocks/companyid-2269153.cms | quote_2269153.html |
| 2026-10-07T21:07:59.071994+05:30 | 200 | https://economictimes.indiatimes.com/union-bank-of-india/stocks/companyid-12261.cms | quote_12261.html |
| 2026-10-07T21:07:59.164779+05:30 | 200 | https://economictimes.indiatimes.com/lic-housing-finance-ltd/stocks/companyid-10823.cms | quote_10823.html |
| 2026-10-07T21:07:59.238311+05:30 | 200 | https://economictimes.indiatimes.com/india-cements-ltd/stocks/companyid-13550.cms | quote_13550.html |
| 2026-10-07T21:07:59.238499+05:30 | 200 | https://economictimes.indiatimes.com/kei-industries-ltd/stocks/companyid-8311.cms | quote_8311.html |
| 2026-10-07T21:07:59.490504+05:30 | 200 | https://economictimes.indiatimes.com/pnb-housing-finance-ltd/stocks/companyid-4749.cms | quote_4749.html |
| 2026-10-07T21:07:59.680796+05:30 | 200 | https://economictimes.indiatimes.com/rainbow-childrens-medicare-ltd/stocks/companyid-42272.cms | quote_42272.html |
| 2026-10-07T21:07:59.913728+05:30 | 200 | https://economictimes.indiatimes.com/lt-foods-ltd/stocks/companyid-18545.cms | quote_18545.html |
| 2026-10-07T21:08:00.070450+05:30 | 200 | https://economictimes.indiatimes.com/jubilant-foodworks-ltd/stocks/companyid-16224.cms | quote_16224.html |
| 2026-10-07T21:08:00.191051+05:30 | 200 | https://economictimes.indiatimes.com/punjab-national-bank/stocks/companyid-11585.cms | quote_11585.html |
| 2026-10-07T21:08:00.247678+05:30 | 200 | https://economictimes.indiatimes.com/angel-one-ltd/stocks/companyid-31183.cms | quote_31183.html |
| 2026-10-07T21:08:00.362765+05:30 | 200 | https://economictimes.indiatimes.com/billionbrains-garage-ventures-ltd/stocks/companyid-2282831.cms | quote_2282831.html |
| 2026-10-07T21:08:00.554929+05:30 | 200 | https://economictimes.indiatimes.com/gillette-india-ltd/stocks/companyid-13567.cms | quote_13567.html |
| 2026-10-07T21:08:00.646350+05:30 | 200 | https://economictimes.indiatimes.com/great-eastern-shipping-company-ltd/stocks/companyid-13697.cms | quote_13697.html |
| 2026-10-07T21:08:00.921437+05:30 | 200 | https://economictimes.indiatimes.com/one97-communications-ltd/stocks/companyid-2017785.cms | quote_2017785.html |
| 2026-10-07T21:08:00.932853+05:30 | 200 | https://economictimes.indiatimes.com/aditya-infotech-ltd/stocks/companyid-46238.cms | quote_46238.html |
| 2026-10-07T21:08:01.025269+05:30 | 200 | https://economictimes.indiatimes.com/balrampur-chini-mills-ltd/stocks/companyid-12477.cms | quote_12477.html |
| 2026-10-07T21:08:01.204301+05:30 | 200 | https://economictimes.indiatimes.com/lemon-tree-hotels-ltd/stocks/companyid-33652.cms | quote_33652.html |
| 2026-10-07T21:08:01.310418+05:30 | 200 | https://economictimes.indiatimes.com/adani-green-energy-ltd/stocks/companyid-64847.cms | quote_64847.html |
| 2026-10-07T21:08:01.505360+05:30 | 200 | https://economictimes.indiatimes.com/deepak-fertilisers-petrochemicals-corporation-ltd/stocks/companyid-13837.cms | quote_13837.html |
| 2026-10-07T21:08:01.581994+05:30 | 200 | https://economictimes.indiatimes.com/aarti-industries-ltd/stocks/companyid-11400.cms | quote_11400.html |
| 2026-10-07T21:08:01.603633+05:30 | 200 | https://economictimes.indiatimes.com/bajaj-housing-finance-ltd/stocks/companyid-60813.cms | quote_60813.html |
| 2026-10-07T21:08:01.794562+05:30 | 200 | https://economictimes.indiatimes.com/canara-hsbc-life-insurance-company-ltd/stocks/companyid-21875.cms | quote_21875.html |
| 2026-10-07T21:08:01.932335+05:30 | 200 | https://economictimes.indiatimes.com/asahi-india-glass-ltd/stocks/companyid-14039.cms | quote_14039.html |
| 2026-10-07T21:08:02.153642+05:30 | 200 | https://economictimes.indiatimes.com/polycab-india-ltd/stocks/companyid-33820.cms | quote_33820.html |
| 2026-10-07T21:08:02.212020+05:30 | 200 | https://economictimes.indiatimes.com/fortis-healthcare-ltd/stocks/companyid-16648.cms | quote_16648.html |
| 2026-10-07T21:08:02.345523+05:30 | 200 | https://economictimes.indiatimes.com/transformers-rectifiers-india-ltd/stocks/companyid-20444.cms | quote_20444.html |
| 2026-10-07T21:08:02.456910+05:30 | 200 | https://economictimes.indiatimes.com/mtar-technologies-ltd/stocks/companyid-46140.cms | quote_46140.html |
| 2026-10-07T21:08:02.485298+05:30 | 200 | https://economictimes.indiatimes.com/indian-bank/stocks/companyid-8614.cms | quote_8614.html |
| 2026-10-07T21:08:02.645902+05:30 | 200 | https://economictimes.indiatimes.com/kotak-mahindra-bank-ltd/stocks/companyid-12161.cms | quote_12161.html |
| 2026-10-07T21:08:02.661660+05:30 | 200 | https://economictimes.indiatimes.com/astral-ltd/stocks/companyid-15686.cms | quote_15686.html |
| 2026-10-07T21:08:02.887850+05:30 | 200 | https://economictimes.indiatimes.com/jk-cement-ltd/stocks/companyid-16847.cms | quote_16847.html |
| 2026-10-07T21:08:03.161953+05:30 | 200 | https://economictimes.indiatimes.com/jain-resource-recycling-ltd/stocks/companyid-2260247.cms | quote_2260247.html |
| 2026-10-07T21:08:03.198362+05:30 | 200 | https://economictimes.indiatimes.com/ge-vernova-td-india-ltd/stocks/companyid-13800.cms | quote_13800.html |
| 2026-10-07T21:08:03.217206+05:30 | 200 | https://economictimes.indiatimes.com/welspun-corp-ltd/stocks/companyid-5032.cms | quote_5032.html |
| 2026-10-07T21:08:03.351517+05:30 | 200 | https://economictimes.indiatimes.com/multi-commodity-exchange-of-india-ltd/stocks/companyid-16571.cms | quote_16571.html |
| 2026-10-07T21:08:03.681614+05:30 | 200 | https://economictimes.indiatimes.com/capri-global-capital-ltd/stocks/companyid-6183.cms | quote_6183.html |
| 2026-10-07T21:08:03.696533+05:30 | 200 | https://economictimes.indiatimes.com/bse-ltd/stocks/companyid-2809.cms | quote_2809.html |
| 2026-10-07T21:08:03.746012+05:30 | 200 | https://economictimes.indiatimes.com/avenue-supermarts-ltd/stocks/companyid-45987.cms | quote_45987.html |
| 2026-10-07T21:08:03.866542+05:30 | 200 | https://economictimes.indiatimes.com/karur-vysya-bank-ltd/stocks/companyid-12258.cms | quote_12258.html |
| 2026-10-07T21:08:03.877797+05:30 | 200 | https://economictimes.indiatimes.com/apollo-tyres-ltd/stocks/companyid-63.cms | quote_63.html |
| 2026-10-07T21:08:04.287797+05:30 | 200 | https://economictimes.indiatimes.com/tega-industries-ltd/stocks/companyid-43277.cms | quote_43277.html |
| 2026-10-07T21:08:04.370251+05:30 | 200 | https://economictimes.indiatimes.com/supreme-industries-ltd/stocks/companyid-12969.cms | quote_12969.html |
| 2026-10-07T21:08:04.533407+05:30 | 200 | https://economictimes.indiatimes.com/aavas-financiers-ltd/stocks/companyid-35834.cms | quote_35834.html |
| 2026-10-07T21:08:04.546115+05:30 | 200 | https://economictimes.indiatimes.com/oil-india-ltd/stocks/companyid-4547.cms | quote_4547.html |
| 2026-10-07T21:08:04.555286+05:30 | 200 | https://economictimes.indiatimes.com/bharti-airtel-ltd/stocks/companyid-2718.cms | quote_2718.html |
| 2026-10-07T21:08:05.038797+05:30 | 200 | https://economictimes.indiatimes.com/shyam-metalics-and-energy-ltd/stocks/companyid-2011527.cms | quote_2011527.html |
| 2026-10-07T21:08:05.062372+05:30 | 200 | https://economictimes.indiatimes.com/piramal-pharma-ltd/stocks/companyid-2094561.cms | quote_2094561.html |
| 2026-10-07T21:08:05.166465+05:30 | 200 | https://economictimes.indiatimes.com/lg-electronics-india-ltd/stocks/companyid-4476.cms | quote_4476.html |
| 2026-10-07T21:08:05.187902+05:30 | 200 | https://economictimes.indiatimes.com/avanti-feeds-ltd/stocks/companyid-6724.cms | quote_6724.html |
| 2026-10-07T21:08:05.430286+05:30 | 200 | https://economictimes.indiatimes.com/canara-bank/stocks/companyid-9218.cms | quote_9218.html |
| 2026-10-07T21:08:05.440978+05:30 | 200 | https://economictimes.indiatimes.com/swan-corp-ltd/stocks/companyid-11965.cms | quote_11965.html |
| 2026-10-07T21:08:05.670836+05:30 | 200 | https://economictimes.indiatimes.com/alkem-laboratories-ltd/stocks/companyid-15059.cms | quote_15059.html |
| 2026-10-07T21:08:05.793029+05:30 | 200 | https://economictimes.indiatimes.com/siemens-energy-india-ltd/stocks/companyid-2258438.cms | quote_2258438.html |
| 2026-10-07T21:08:05.922295+05:30 | 200 | https://economictimes.indiatimes.com/icici-bank-ltd/stocks/companyid-9194.cms | quote_9194.html |
| 2026-10-07T21:08:06.070699+05:30 | 200 | https://economictimes.indiatimes.com/federal-bank-ltd/stocks/companyid-9211.cms | quote_9211.html |
| 2026-10-07T21:08:06.104211+05:30 | 200 | https://economictimes.indiatimes.com/granules-india-ltd/stocks/companyid-6991.cms | quote_6991.html |
| 2026-10-07T21:08:06.307078+05:30 | 200 | https://economictimes.indiatimes.com/bank-of-india/stocks/companyid-11964.cms | quote_11964.html |
| 2026-10-07T21:08:06.327863+05:30 | 200 | https://economictimes.indiatimes.com/hexaware-technologies-ltd/stocks/companyid-2254981.cms | quote_2254981.html |
| 2026-10-07T21:08:06.350790+05:30 | 200 | https://economictimes.indiatimes.com/kajaria-ceramics-ltd/stocks/companyid-13489.cms | quote_13489.html |
| 2026-10-07T21:08:06.705832+05:30 | 200 | https://economictimes.indiatimes.com/zydus-wellness-ltd/stocks/companyid-6816.cms | quote_6816.html |
| 2026-10-07T21:08:06.891195+05:30 | 200 | https://economictimes.indiatimes.com/ola-electric-mobility-ltd/stocks/companyid-2206544.cms | quote_2206544.html |
| 2026-10-07T21:08:06.916033+05:30 | 200 | https://economictimes.indiatimes.com/indian-energy-exchange-ltd/stocks/companyid-20870.cms | quote_20870.html |
| 2026-10-07T21:08:06.970517+05:30 | 200 | https://economictimes.indiatimes.com/thangamayil-jewellery-ltd/stocks/companyid-30963.cms | quote_30963.html |
| 2026-10-07T21:08:07.153703+05:30 | 200 | https://economictimes.indiatimes.com/sumitomo-chemical-india-ltd/stocks/companyid-49672.cms | quote_49672.html |
| 2026-10-07T21:08:07.227731+05:30 | 200 | https://economictimes.indiatimes.com/afcons-infrastructure-ltd/stocks/companyid-11878.cms | quote_11878.html |
| 2026-10-07T21:08:07.320848+05:30 | 200 | https://economictimes.indiatimes.com/power-finance-corporation-ltd/stocks/companyid-4519.cms | quote_4519.html |
| 2026-10-07T21:08:07.361649+05:30 | 200 | https://economictimes.indiatimes.com/central-depository-services-india-ltd/stocks/companyid-4259.cms | quote_4259.html |
| 2026-10-07T21:08:07.530838+05:30 | 200 | https://economictimes.indiatimes.com/fsn-e-commerce-ventures-ltd/stocks/companyid-2017563.cms | quote_2017563.html |
| 2026-10-07T21:08:07.597764+05:30 | 200 | https://economictimes.indiatimes.com/oracle-financial-services-software-ltd/stocks/companyid-3160.cms | quote_3160.html |
| 2026-10-07T21:08:07.764158+05:30 | 200 | https://economictimes.indiatimes.com/central-bank-of-india/stocks/companyid-11944.cms | quote_11944.html |
| 2026-10-07T21:08:07.790507+05:30 | 200 | https://economictimes.indiatimes.com/amber-enterprises-india-ltd/stocks/companyid-67404.cms | quote_67404.html |
| 2026-10-07T21:08:07.807301+05:30 | 200 | https://economictimes.indiatimes.com/apar-industries-ltd/stocks/companyid-12150.cms | quote_12150.html |
| 2026-10-07T21:08:08.157623+05:30 | 200 | https://economictimes.indiatimes.com/bank-of-baroda/stocks/companyid-12040.cms | quote_12040.html |
| 2026-10-07T21:08:08.260324+05:30 | 200 | https://economictimes.indiatimes.com/radico-khaitan-ltd/stocks/companyid-12315.cms | quote_12315.html |
| 2026-10-07T21:08:08.323416+05:30 | 200 | https://economictimes.indiatimes.com/motherson-sumi-wiring-india-ltd/stocks/companyid-2024281.cms | quote_2024281.html |
| 2026-10-07T21:08:08.352546+05:30 | 200 | https://economictimes.indiatimes.com/indiamart-intermesh-ltd/stocks/companyid-50224.cms | quote_50224.html |
| 2026-10-07T21:08:08.503506+05:30 | 200 | https://economictimes.indiatimes.com/jm-financial-ltd/stocks/companyid-12633.cms | quote_12633.html |
| 2026-10-07T21:08:08.739558+05:30 | 200 | https://economictimes.indiatimes.com/general-insurance-corporation-of-india/stocks/companyid-12266.cms | quote_12266.html |
| 2026-10-07T21:08:08.990535+05:30 | 200 | https://economictimes.indiatimes.com/swiggy-ltd/stocks/companyid-2232501.cms | quote_2232501.html |
| 2026-10-07T21:08:09.027810+05:30 | 200 | https://economictimes.indiatimes.com/sun-tv-network-ltd/stocks/companyid-17994.cms | quote_17994.html |
| 2026-10-07T21:08:09.056857+05:30 | 200 | https://economictimes.indiatimes.com/coal-india-ltd/stocks/companyid-11822.cms | quote_11822.html |
| 2026-10-07T21:08:09.356348+05:30 | 200 | https://economictimes.indiatimes.com/sansera-engineering-ltd/stocks/companyid-49492.cms | quote_49492.html |
| 2026-10-07T21:09:37.398388+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/5446-32b4daca50b1e144.js | stockjs_0.html |
| 2026-10-07T21:09:37.398972+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/3955-9090b509adbf2891.js | stockjs_1.html |
| 2026-10-07T21:09:37.399268+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/2067-c9210c83d42a747a.js | stockjs_2.html |
| 2026-10-07T21:09:37.399643+05:30 | 200 | https://economictimes.indiatimes.com/marketsweb/_next/static/chunks/app/%5BcompanySeoName%5D/stocks/%5B...companyId%5D/page-de8c6f1f004e6946.js | stockjs_3.html |
| 2026-10-07T21:09:37.649390+05:30 | 200 | https://etapi.indiatimes.com/et-screener/v2/intraday-stats | api_gainers_page2.html |
| 2026-10-07T21:09:53.524659+05:30 | 200 | https://etinsights.indiatimes.com/ET_TechnicalIndicator/getTechnicalMobileDetail?scripCode=CHENNPETROEQ&companytype=equity | technical_detail.html |
| 2026-10-07T21:10:13.895200+05:30 | 200 | https://economictimes.indiatimes.com/stocks/marketstats-technicals/rsi-above-80 | rsi_page.html |
