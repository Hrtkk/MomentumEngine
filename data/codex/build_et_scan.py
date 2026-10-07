import csv,json,datetime,decimal,re
from pathlib import Path
BASE=Path(__file__).resolve().parent
D=decimal.Decimal
load=lambda n:json.loads((BASE/(n+'.html')).read_text())
fields=lambda r:{v['keyId']:v.get('filterFormatValue') for v in r['data']}
g=load('api_gainers');g2=load('api_gainers_page2');tech=load('api_technicals')
rows=g['dataList'];allg=rows+g2['dataList'];ti={r['assetId']:fields(r) for r in tech['dataList']}
smas=load('api_sma')['dataList']+load('api_sma_below')['dataList'];si={r['assetId']:fields(r) for r in smas}
quotes={r['assetId']:r['company'] for r in json.loads((BASE/'quotes_parsed.json').read_text())}
assert len(rows)==100 and len(allg)==149 and len({r['assetId'] for r in allg})==149
assert all(D(fields(a)['percentChange'])>=D(fields(b)['percentChange']) for a,b in zip(allg,allg[1:]))
assert {r['assetId'] for r in rows}==set(ti)
headers='rank,symbol,name,close,pct_change,volume,sma20,sma50,sma200,rsi14,high52w,low52w,source_url'.split(',')
output=[];audit=[];vol_diffs=[]
for rank,r in enumerate(rows,1):
 id=r['assetId'];v=fields(r);t=ti[id];s=si[id];q=quotes[id];n=q['nse'];raw=r['assetSymbol']
 assert q['nifty500'] is True and n['updatedDateTime'].startswith('2026-10-07')
 assert n['symbol']==raw and D(str(n['current']))==D(v['lastTradedPrice']) and D(str(n['percentChange']))==D(v['percentChange'])
 assert t['currentSma20']==s['currentSma20'] and t['currentSma50']==s['currentSma50']
 symbol=raw[:-2] if raw.endswith(('EQ','BE')) else raw
 url='https://economictimes.indiatimes.com/'+r['assetSeoName']+'/stocks/companyid-'+id+'.cms'
 # currentRsi is retained in audit; retrieved metadata does not certify a 14-session period.
 out=dict(zip(headers,[rank,symbol,r['assetName'],v['lastTradedPrice'],v['percentChange'],v['volume'],t['currentSma20'],t['currentSma50'],s['currentSma200'],'',n.get('fiftyTwoWeekHighPrice',''),n.get('fiftyTwoWeekLowPrice',''),url]))
 assert D(str(out['high52w']))>=D(str(out['low52w']))
 output.append(out)
 audit.append({'rank':rank,'symbol':symbol,'et_symbol':raw,'asset_id':id,'quote_updated_ist':n['updatedDateTime'],'et_currentRsi':t['currentRsi'],'rsi_period_verified':False,'quote_volume':n['volume'],'screener_volume':v['volume'],'source_url':url})
 if D(v['volume'])!=D(str(n['volume'])):vol_diffs.append((symbol,v['volume'],n['volume']))
assert len({r['symbol'] for r in output})==100
csvpath=BASE/'et_top100_2026-10-07.csv'
with csvpath.open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=headers);w.writeheader();w.writerows(output)
(BASE/'et_row_audit.json').write_text(json.dumps(audit,indent=2))
missing={k:sum(r[k] in ['',None] for r in output) for k in headers}
logs=json.loads((BASE/'et_retrieval_log.json').read_text())
ist=datetime.timezone(datetime.timedelta(hours=5,minutes=30))
ts=lambda n:datetime.datetime.fromtimestamp(n/1000,ist).isoformat()
notes=['# Independent ET preliminary scan — 7 October 2026','',
'Output: `et_top100_2026-10-07.csv`, **100 data rows** (plus header), ranked by ET one-day percentage gain descending within its Nifty 500 universe. No NSE bhavcopy or Claude pipeline data was used to populate the CSV.',
'', '**Price qualification:** `close` contains ET’s post-session `lastTradedPrice` / quote `current`, not a separately certified NSE official closing-auction/bhavcopy close. All 100 quote prices and percentage changes agree with the screener. This is a preliminary ET cross-check; compare this distinction when reconciling with bhavcopy.',
'', '**RSI qualification:** `rsi14` is blank for all 100 rows. ET exposes `currentRsi` (label “RSI Current”) for all 100, but the retrieved screener metadata does not specify the lookback period. A 14-session lookback was not assumed. The exact ET values are preserved as `et_currentRsi` in `et_row_audit.json` and in `api_technicals.html` (JSON response).',
'', '## Session, ranking and coverage','',
f'- ET snapshot `unixDateTime`: {g["unixDateTime"]} = **{ts(g["unixDateTime"])}**. Both overview and technical responses have this timestamp; the retrieved stock quotes are all dated 7 October 2026, after the regular-session close.',
f'- Individual NSE quote timestamps range from {min(a["quote_updated_ist"] for a in audit)} to {max(a["quote_updated_ist"] for a in audit)} IST.',
'- Live page `selectedFilter` explicitly identifies `Nifty 500`, `indexId=2371`, `exchange=nse`; request uses `filterType=index`, `filterValue=[2371]`, `apiType=gainers`, `duration=1D`.',
'- Page 1 contains 100 gainers; page 2 contains 49. All 149 are unique and non-increasing by percentage gain. The first 100 are retained in ET’s original order, including tie order. Each selected stock’s individual quote metadata also has `nifty500=true`.',
f'- Rank 100: {output[-1]["symbol"]}, {output[-1]["pct_change"]}%; rank 101: {allg[100]["assetSymbol"]}, {fields(allg[100])["percentChange"]}%.',
'- SMA above/below-20 screens returned 138 + 359 = 497 unique stocks; together they cover all selected 100. The top-100 Technicals view also covers all 100. SMA20 and SMA50 agree between these sources.',
'', '## Fields and missing values','',
'Numeric values use ET’s `filterFormatValue`, not its rounded display `value`. Currency is INR; `pct_change` is percentage points (14.7 means +14.7%); volume is shares, not turnover.',
'', '| CSV field | ET field / treatment | Missing rows |','|---|---|---:|']
mapping={'rank':'1–100 in ET gainers order','symbol':'assetSymbol with terminal EQ or BE series suffix removed','name':'assetName','close':'lastTradedPrice (post-close price proxy; see qualification above)','pct_change':'percentChange','volume':'volume from gainers overview','sma20':'currentSma20','sma50':'currentSma50','sma200':'currentSma200 from above/below-SMA20 screens','rsi14':'Blank: currentRsi exists, but 14-period definition not verified','high52w':'company.nse.fiftyTwoWeekHighPrice','low52w':'company.nse.fiftyTwoWeekLowPrice','source_url':'Fetched individual ET stock quote URL; common screener/API sources below'}
notes += [f'| {k} | {mapping[k]} | {missing[k]} |' for k in headers]
notes += ['', '## Reference inspection and data-quality limitations','',
'- Inspected `momentum-engine/reference/gainers_technical_scan_2026-10-06.html` and `gainers_momentum_2026-10-07.html` read-only. They are generated reports, not raw ET pages. They name ET market stats / technical screeners, but contain no exact market-stats or screener URL; only per-stock ET company links. The first report embeds 100 rows; the second embeds 100 previous-day and 100 current-day rows.',
'- Reference fields include symbol/name/company URL, price, daily change, RSI, relative distance to SMAs and 52-week high, returns, support/risk and derived scores/signals. The 6 October report includes hi52 and d50; the 7 October report does not contain raw volume, SMA20/50/200 or both raw 52-week extrema. No values were copied or reverse-engineered from these reports.',
'- The 6 October reference explicitly describes previous-day technical indicators combined with intraday prices. The live technical responses have a 7 October snapshot timestamp but no per-indicator price-as-of date. Do not interpret that response timestamp as proof the SMAs/RSI incorporate the 7 October close. A technical-detail probe for CHENNPETRO returned `currentDto.priceDate` = 6 October 2026 for its pivot/ATR/Heikin-Ashi data, even though its update timestamp is on 7 October. This establishes lag in that endpoint, not the exact vintage of every screener indicator.',
'- ET symbols contain series suffixes. EQ was removed for 98 stocks and BE for HFCL and MTARTECH. The raw identifiers are retained in `et_row_audit.json`. For a bhavcopy join, use the corresponding EQ/BE series; do not silently omit BE stocks.',
'- The initially probed legacy URL used indexid=2370; it returned HTTP 200 but did not identify Nifty 500 and was not used for the output. The live page establishes 2371 as the correct ET index ID.',
'- Some rendered prices are rounded to integers, while the embedded raw field retains decimals. The CSV preserves raw field precision. No prices, indicators, or percentage changes were recomputed, imputed, or copied from the reference reports.',
f'- {len(vol_diffs)} quote pages have volume differences from the gainers overview. The overview is retained consistently for every CSV volume. Both values are recorded below. Price and percentage-change discrepancies between these two ET sources: 0/100.',
'- 52-week highs/lows come from NSE quote data only. Corporate-action adjustment methodology and official closing-price equivalence were not independently established.',
'- All attempted HTTP requests returned 200; no access block occurred. HTTP success alone was not treated as evidence of correct content. Parsed stock IDs, dates, universe flags, row counts and sorting were validated.',
'', '| Symbol | Gainers overview volume (CSV) | Individual NSE quote volume |','|---|---:|---:|']
notes += [f'| {s} | {a} | {b} |' for s,a,b in vol_diffs]
notes += ['', '## Working endpoints and request bodies','',
'Public data endpoints were discovered from JavaScript referenced by the live ET pages. Requests used Python 3 standard-library `urllib.request`, with a browser User-Agent. No authenticated session or subscription credentials were used.',
'', '- Page: https://economictimes.indiatimes.com/stocks/marketstats/top-gainers',
'- Technical page: https://economictimes.indiatimes.com/stocks/marketstats-technicals/ltp-above-sma-20',
'- `POST https://etapi.indiatimes.com/et-screener/v2/intraday-stats`: overview `viewId=6925`; Technicals `viewId=6918`.',
'- `POST https://etapi.indiatimes.com/et-screener/v2/technical-data`: `viewId=6986`, `firstOperand=lastTradedPrice`, `secondOperand=currentSma20`, `operationType=Above` or `Below`, Nifty 500 filter, `pagesize=500`.',
'', 'Exact POST bodies (all are read-only data queries):','']
for log in logs:
 if log.get('request_body') is not None:
  notes += [f'### {Path(log["body_file"]).name}',f'URL: {log["url"]}',f'Retrieved: {log["retrieved_ist"]}; HTTP {log.get("status")}.','```json',json.dumps(log['request_body'],indent=2),'```','']
notes += ['## Complete retrieval ledger (IST)','', 'Timestamps below record request start in IST (+05:30). Exact response headers, request bodies and raw response filenames are in `et_retrieval_log.json`. Raw `.html` files for API calls contain JSON, despite the filename extension. Saved responses support reproducibility because these live URLs will change in later sessions.','', '| Retrieval timestamp IST | HTTP | Exact URL | Saved response |','|---|---:|---|---|']
for l in logs:notes.append(f'| {l["retrieved_ist"]} | {l.get("status",l.get("error","unknown"))} | {l["url"]} | {Path(l["body_file"]).name} |')
(BASE/'et_scan_notes.md').write_text('\n'.join(notes)+'\n')
with csvpath.open(newline='') as f:
 reread=list(csv.DictReader(f));assert len(reread)==100 and list(reread[0])==headers
print(json.dumps({'rows':len(output),'missing':missing,'first':output[0],'last':output[-1],'requests':len(logs),'volume_discrepancies':len(vol_diffs)},indent=2))
