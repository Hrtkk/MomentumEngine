"""Retrospective report with fresh official EOD observations and cutoff-aware news."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
import json,hashlib,tempfile,os,fcntl
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[2];R=ROOT/'research';I=R/'inputs/2026-10-13_2000';TZ=ZoneInfo('Asia/Kolkata');CUTOFF='2026-10-13T20:00:00+05:30'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False,default=str)+'\n')
def clean(x):return float(x) if pd.notna(x) and np.isfinite(x) else None
def jsonl(p,rows):p.write_text(''.join(json.dumps(x,ensure_ascii=False,allow_nan=False)+'\n' for x in rows))
def verify(p):
 m=json.loads((p/'manifest.json').read_text());assert m['committed']
 for a in m['artifacts']:assert sha(p/a['path'])==a['sha256']
def main():
 with (R/'state/orchestrator/writer.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  started=datetime.now(TZ).isoformat()
  original=R/'stock_reports/evidence_df51d64ad28b';verify(original)
  old=[json.loads(x) for x in (original/'stocks.jsonl').read_text().splitlines()];stocks={x['symbol']:x for x in old}
  td=R/'runs/2026-10-09_diagnostic_f851eb37ee38/routine_01/routine_01_a01';verify(td)
  universe=[json.loads(x)['symbol'] for fn in ['metrics.jsonl','quarantine.jsonl'] for x in (td/fn).read_text().splitlines()]
  assert len(set(universe))==500
  hist_paths=[ROOT/f'experiments/data/pit/bhav_{y}.parquet' for y in [2025,2026]]
  b=pd.concat([pd.read_parquet(p) for p in hist_paths],ignore_index=True);b['date']=pd.to_datetime(b['date'])
  identities=b.sort_values('date').drop_duplicates(['symbol','series'],keep='last').set_index(['symbol','series'])['isin']
  raw={};extra=[]
  rename={'SYMBOL':'symbol','SERIES':'series','DATE1':'date','OPEN_PRICE':'open','HIGH_PRICE':'high','LOW_PRICE':'low','CLOSE_PRICE':'close','PREV_CLOSE':'prev_close','TTL_TRD_QNTY':'volume','NO_OF_TRADES':'trades'}
  for date in ['2026-10-12','2026-10-13']:
   d=pd.read_csv(I/f'bhav_{date}.csv');d.columns=d.columns.str.strip();d['SYMBOL']=d.SYMBOL.str.strip();d['SERIES']=d.SERIES.str.strip()
   assert (pd.to_datetime(d.DATE1.str.strip(),format='%d-%b-%Y').dt.strftime('%Y-%m-%d')==date).all()
   raw[date]=d;z=d.rename(columns=rename);z['date']=pd.to_datetime(z.date.str.strip(),format='%d-%b-%Y');z['value']=pd.to_numeric(z.TURNOVER_LACS,errors='coerce')*100000
   z['isin']=[identities.get((s,se),None) for s,se in zip(z.symbol,z.series)];extra.append(z[b.columns])
  b=pd.concat([b,*extra],ignore_index=True)
  eq=b[(b.series=='EQ')&b['isin'].astype(str).str.startswith('INE')].copy()
  duplicates=set(eq.loc[eq.duplicated(['date','symbol'],keep=False),'symbol']);eq=eq.drop_duplicates(['date','symbol'],keep=False)
  dates=pd.DatetimeIndex(sorted(eq.date.unique()));date=pd.Timestamp('2026-10-13');previous=pd.Timestamp('2026-10-12')
  pivot=lambda col:eq.pivot(index='date',columns='symbol',values=col).reindex(dates)
  c,h,l,v=[pivot(k) for k in ['close','high','low','volume']]
  rv=v/v.shift(1).rolling(20,min_periods=20).median();daily=c/c.shift(1)-1
  highs={k:h.shift(1).rolling(k,min_periods=k).max() for k in [20,252]};mas={k:c.rolling(k,min_periods=k).mean() for k in [50,200]}
  ca_path=ROOT/'experiments/data/pit/ca.parquet';ca=pd.read_parquet(ca_path);ca['ex']=pd.to_datetime(ca.exDate,format='%d-%b-%Y',errors='coerce')
  action_window=set(ca[(ca.ex>=dates[-321])&(ca.ex<=date)].symbol)
  recent_ca=json.loads((I/'corporate_actions.json').read_text());recent_symbols={x['symbol'] for x in recent_ca};action_window|=recent_symbols
  latest=raw['2026-10-13'];latest=latest[latest.SERIES=='EQ'].copy();prevraw=raw['2026-10-12'];prevraw=prevraw[prevraw.SERIES=='EQ'].set_index('SYMBOL')
  latest['nominal_return_pct']=(latest.CLOSE_PRICE/latest.PREV_CLOSE-1)*100
  valid=latest[(latest.PREV_CLOSE>0)&(latest.CLOSE_PRICE>0)&np.isfinite(latest.nominal_return_pct)]
  idx=pd.read_csv(I/'index_2026-10-13.csv');idx12=pd.read_csv(I/'index_2026-10-12.csv');idx500=idx[idx['Index Name'].str.strip()=='Nifty 500'].iloc[0]
  idx50012=idx12[idx12['Index Name'].str.strip()=='Nifty 500'].iloc[0]
  benchmark_pct=(float(idx500['Closing Index Value'])/float(idx50012['Closing Index Value'])-1)*100
  evaluations=[];signals=[];quarantine=[]
  for sym in universe:
   reasons=[]
   if sym in duplicates:reasons.append('DUPLICATE_SYMBOL')
   if sym in action_window:reasons.append('ACTION_IN_LOOKBACK')
   if sym not in c.columns or not pd.notna(c.at[date,sym]):reasons.append('MISSING_CURRENT_EQ')
   elif not c[sym].tail(321).notna().all():reasons.append('HISTORY_GAPS')
   if reasons:quarantine.append({'symbol':sym,'reasons':reasons});continue
   events=[]
   if daily.at[date,sym]>.05 and rv.at[date,sym]>2:events.append('PRICE_VOLUME_ANOMALY')
   for window in [20,252]:
    if c.at[date,sym]>highs[window].at[date,sym]:events.append(f'ABOVE_PRIOR_{window}_SESSION_HIGH')
   for window in [50,200]:
    if c.at[previous,sym]<=mas[window].at[previous,sym] and c.at[date,sym]>mas[window].at[date,sym]:events.append(f'CROSSED_ABOVE_SMA{window}')
   row={'symbol':sym,'security_id':identities.get((sym,'EQ')),'session':'2026-10-13','close_inr':clean(c.at[date,sym]),'return_pct':clean(daily.at[date,sym]*100),'relative_volume':clean(rv.at[date,sym]),'events':events,'production_eligible':False,'calculation_version':'r1-cutoff-20261013-1'};evaluations.append(row)
   for ev in events:signals.append({**row,'event_type':ev,'finding_id':hashlib.sha256(f'{sym}:{ev}:2026-10-13'.encode()).hexdigest()[:20]})
   if events:
    stocks.setdefault(sym,{'symbol':sym,'record_kind':'RESEARCH_LEAD','qualified':False,'company_events':[],'next_check':'Verify current signal persistence, business quality and corporate-action completeness.','owner':'Codex verification; Claude research'})['technical']=row
  news=json.loads((I/'news_updates.json').read_text());excluded=[];accepted=[]
  for event in news:
   pub=event['published_at']
   if pub is None:excluded.append({**event,'cutoff_status':'PUBLICATION_TIME_UNKNOWN'});continue
   if 'T' in pub and datetime.fromisoformat(pub)>datetime.fromisoformat(CUTOFF):excluded.append({**event,'cutoff_status':'AFTER_CUTOFF'});continue
   if len(pub)==10 and pub=='2026-10-13':excluded.append({**event,'cutoff_status':'SAME_DAY_TIME_UNKNOWN'});continue
   event['cutoff_status']='BEFORE_CUTOFF';accepted.append(event)
   row=stocks.setdefault(event['symbol'],{'symbol':event['symbol'],'record_kind':'RESEARCH_LEAD','qualified':False,'technical':None,'company_events':[],'owner':'Codex verification; Claude research'})
   row.setdefault('new_events',[]).append(event);row['next_check']=event['next_check']
  rawindex=latest.set_index('SYMBOL');oldset={x['symbol'] for x in old};rows=[]
  for sym,row in sorted(stocks.items()):
   row['new_to_report']=sym not in oldset
   if sym in rawindex.index and not isinstance(rawindex.loc[sym],pd.DataFrame):
    q=rawindex.loc[sym];oldprice=c.at[pd.Timestamp('2026-10-09'),sym] if sym in c else np.nan
    shift=(q.CLOSE_PRICE/oldprice-1)*100 if pd.notna(oldprice) and oldprice>0 else np.nan
    source_return=clean(q.nominal_return_pct) if sym not in recent_symbols else None
    row['current_stats']={'session':'2026-10-13','close_inr':clean(q.CLOSE_PRICE),'nominal_daily_return_pct':source_return,'raw_volume':int(q.TTL_TRD_QNTY),'traded_value_inr_crore':clean(q.TURNOVER_LACS/100),'volume_ratio_prior20':clean(rv.at[date,sym]) if sym in rv and sym not in recent_symbols else None,'nominal_return_since_oct9_pct':clean(shift) if sym not in recent_symbols else None,'daily_excess_vs_nifty500_pp':source_return-benchmark_pct if source_return is not None else None,'adjustment_verified':False,'price_action_flag':sym in recent_symbols}
   else:row['current_stats']=None
   rows.append(row)
  source_paths=hist_paths+[ca_path,*I.glob('*.csv'),I/'fetch_manifest.json',I/'corporate_actions.json',I/'news_updates.json']
  input_versions={str(p.relative_to(ROOT)):sha(p) for p in source_paths}
  stats={'cutoff_at':CUTOFF,'compiled_at':started,'official_eod_session':'2026-10-13','official_file_first_seen_at':json.loads((I/'fetch_manifest.json').read_text())[2]['retrieved_at'],'file_available_before_cutoff_verified':False,'eq_series_rows':len(latest),'valid_nominal_return_rows':len(valid),'advancers':int((valid.nominal_return_pct>0).sum()),'decliners':int((valid.nominal_return_pct<0).sum()),'unchanged':int((valid.nominal_return_pct==0).sum()),'advance_decline_ratio':int((valid.nominal_return_pct>0).sum())/int((valid.nominal_return_pct<0).sum()),'diagnostic_universe':500,'technical_evaluated':len(evaluations),'quarantined':len(quarantine),'new_technical_event_records':len(signals),'fresh_technical_names':len({x['symbol'] for x in signals}),'stock_report_count':len(rows),'prior_stock_count':len(old),'new_names':sorted(set(stocks)-oldset),'retained_prior_names':len(oldset&set(stocks)),'accepted_news_updates':len(accepted),'publication_unknown_excluded':len(excluded),'nifty500_daily_return_pct':benchmark_pct,'indices':[{k:(str(q[k]) if k=='Change(%)' else q[k]) for k in ['Index Name','Closing Index Value','Change(%)']} for _,q in idx[idx['Index Name'].str.strip().isin(['Nifty 50','Nifty 500','Nifty Bank'])].iterrows()]}
  fingerprint=hashlib.sha256(json.dumps(input_versions,sort_keys=True).encode()).hexdigest()[:12];target=R/f'stock_reports/2026-10-13_2000_{fingerprint}';target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():verify(target);print(json.dumps({'reused':True,'report':str(target/'report.md')}));return
  temp=Path(tempfile.mkdtemp(prefix='.pending_',dir=target.parent));save(temp/'stats.json',stats);jsonl(temp/'stocks.jsonl',rows);jsonl(temp/'signals.jsonl',signals);jsonl(temp/'metrics.jsonl',evaluations);jsonl(temp/'quarantine.jsonl',quarantine);jsonl(temp/'news_updates.jsonl',accepted);jsonl(temp/'cutoff_exclusions.jsonl',excluded)
  table=['# Stock research report — 13 October 2026, 20:00 IST','','**Fresh 13 October closing data; targeted news update through the requested cutoff. Status: PARTIAL / diagnostic.**','',f'Compiled {started}. Official files were downloaded at about 20:23, after the cutoff. Their internal dates verify the 13 October closing observations; file publication by 20:00 is not established. This is retrospective reconstruction, not a claim that the full dataset was captured by 20:00.','', '## Statistics','',f'- EQ-series securities: {len(latest)}; valid nominal-return observations: {len(valid)}; advancing {stats["advancers"]}, declining {stats["decliners"]}, unchanged {stats["unchanged"]}; A/D {stats["advance_decline_ratio"]:.2f}. Raw EQ-series breadth is not a certified all-equity investability universe.',f'- Fixed 500-name diagnostic universe: {len(evaluations)} evaluated, {len(quarantine)} quarantined. Price/volume, prior-high and moving-average scans produced {len(signals)} events across {stats["fresh_technical_names"]} securities. ATR/drawdown, sector breadth and full fundamental screens were not refreshed.',f'- Prior queue: {len(old)} names; refreshed report: {len(rows)} names; new names: {", ".join(stats["new_names"]) or "none"}. Retained older leads are not automatically requalified.',f'- Accepted new disclosure updates: {len(accepted)}; cutoff-uncertain excluded records: {len(excluded)}. All event facts retain primary/secondary labels.','', '| Index | Close 13 Oct | Daily change |','| --- | --- | --- |']
  for q in stats['indices']:table.append(f'| {q["Index Name"]} | {q["Closing Index Value"]:,.2f} | {q["Change(%)"]}% |')
  table+=['','Index and price source: [official download manifest]('+str(I/'fetch_manifest.json')+'). Every calculation/input hash is retained in handoff.json. Returns below are nominal price returns, not dividend/entitlement-adjusted total returns.','','## New or updated disclosure names','', '| Stock | Evidence | Verification | 13 Oct close ₹ | Daily move | Next check |','| --- | --- | --- | --- | --- | --- |']
  bysym={x['symbol']:x for x in rows}
  for e in accepted:
   s=bysym[e['symbol']]['current_stats'];price=f'{s["close_inr"]:.2f}' if s else '—';ret=f'{s["nominal_daily_return_pct"]:+.2f}%' if s and s['nominal_daily_return_pct'] is not None else '—'
   table.append(f'| {e["symbol"]} | [{e["fact"]}]({e["source_url"]}) | {e["verification_status"]} | {price} | {ret} | {e["next_check"]} |')
  table+=['','## All named stocks — refreshed statistics','', '| Stock | Close ₹ | Daily nominal % | Since 9 Oct % | Volume / prior20 median | Daily excess vs Nifty500 pp | Current evidence |','| --- | --- | --- | --- | --- | --- | --- |']
  for row in rows:
   s=row['current_stats'];fmt=lambda val:f'{val:+.2f}' if val is not None else '—'
   if s:
    tech=row.get('technical');fresh=tech and tech.get('session')=='2026-10-13';label=', '.join(tech['events']) if fresh else 'Prior lead retained; check latest evidence'
    if row.get('new_events'):label+='; new disclosure'
    table.append(f'| {row["symbol"]} | {s["close_inr"]:.2f} | {fmt(s["nominal_daily_return_pct"])} | {fmt(s["nominal_return_since_oct9_pct"])} | {s["volume_ratio_prior20"]:.2f}× | {fmt(s["daily_excess_vs_nifty500_pp"])} | {label} |' if s['volume_ratio_prior20'] is not None else f'| {row["symbol"]} | {s["close_inr"]:.2f} | {fmt(s["nominal_daily_return_pct"])} | {fmt(s["nominal_return_since_oct9_pct"])} | — | — | Incomplete history/action check |')
  table+=['','## Government spending and project evidence','', '- [L&T-built Samarthak](https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2322795&lang=1&reg=3): announcement at 16:22 on 13 October confirms an execution milestone. No new order value inferred.', '- [NH-22 project](https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2322801&lang=1&reg=3): 16:25 release discusses ₹3,590.73 crore approval from August. It is not a new 13 October allocation; no listed contractor award established.', '- [PM-SETU clusters](https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2322170&lang=1&reg=3): ₹440 crore approved investment for ITI clusters, with AM/NS India participation. No listed supplier order is established. This is not added to road/defence order totals.', '', '## Data and interpretation limits','', '- Official recent corporate-action feed records OLAELEC rights ex-date 13 October. Its historical notice publication time is unknown: listed only as an adjustment-control exclusion, not a cutoff-verified new announcement.', '- HCL original financial PDFs timed out. HCL numbers remain secondary sourced. RBL financial table is primary, but its original immutable publication timestamp is unverified; secondary reporting establishes the 12 October release date.', '- No causal attribution of share-price moves to news. Secondary allegations about insolvency/fraud or corporate events without original verification are not adopted as fact.', '- Existing corporate-action history, identity/calendar completeness and sector benchmarks remain uncertified. The conservative long-window exclusion rule removes even routine dividend names from full technical screening; raw price snapshots remain available separately.', '- Claude economic interpretation/review was not executed. This is factual Codex compilation; none of the names is automatically QUALIFIED. No paper ledgers, frozen source code, Sheet or cloud services were modified.', '', '## Next run','', 'Codex: refresh these same sources, validate original financial/contract filings, compare daily values with the present snapshot and reconcile action entitlements. Claude: assess order economics, earnings quality and business risks when controlled execution is ready. Consume stocks.jsonl, stats.json and handoff.json; preserve older report and all verification gaps.']
  (temp/'report.md').write_text('\n'.join(table)+'\n');save(temp/'handoff.json',{'schema_version':'1.1','artifact_kind':'FACTUAL_STOCK_QUEUE','status':'PARTIAL','production_eligible':False,'cutoff_at':CUTOFF,'compiled_at':started,'executor':'Codex','claude_interpretation_executed':False,'market_asof':'2026-10-13','stock_count':len(rows),'input_versions':input_versions,'upstream_runs':[{'run_dir':str(original.relative_to(ROOT)),'manifest_sha256':sha(original/'manifest.json')}],'source_cursors':{},'news_updates':len(accepted),'next_run':'Resume dates, immutable inputs and verification gaps; do not promote automatically.'})
  artifacts=[{'path':p.name,'sha256':sha(p)} for p in sorted(temp.iterdir())];save(temp/'manifest.json',{'committed':True,'signature':fingerprint,'artifacts':artifacts});verify(temp);assert len(evaluations)+len(quarantine)==500;assert stats['advancers']+stats['decliners']+stats['unchanged']==len(valid)
  os.rename(temp,target);p=R/'state/stock_report/latest.tmp';save(p,{'report_dir':str(target.relative_to(ROOT)),'status':'PARTIAL','stock_count':len(rows),'market_asof':'2026-10-13','cutoff_at':CUTOFF});os.replace(p,R/'state/stock_report/latest.json')
  print(json.dumps({'report':str(target/'report.md'),'stats':stats},default=str))
if __name__=='__main__':main()
