"""Read-only-input R1 diagnostic. No production qualification or book writes."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,os,fcntl,subprocess,tempfile
import pandas as pd
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'research'
TZ=ZoneInfo('Asia/Kolkata')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x): p.write_text(json.dumps(x,indent=2,allow_nan=False,default=str)+'\n')
def finite(x): return float(x) if pd.notna(x) and np.isfinite(x) else None

def main():
 state=R/'state/routine_01';state.mkdir(parents=True,exist_ok=True)
 with (state/'writer.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  started=datetime.now(TZ).isoformat()
  paths=[ROOT/'experiments/data/pit'/f'bhav_{y}.parquet' for y in (2025,2026)]
  ca_path=ROOT/'experiments/data/pit/ca.parquet'
  b=pd.concat([pd.read_parquet(p) for p in paths],ignore_index=True)
  b['date']=pd.to_datetime(b.date).dt.normalize()
  session=b.date.max();dates=pd.DatetimeIndex(sorted(b.date.unique()));i=dates.get_loc(session)
  session_s=session.strftime('%Y-%m-%d')
  raw=ROOT/f'data/raw/bhav/{session_s}.csv'
  d=pd.read_csv(raw);d.columns=d.columns.str.strip()
  internal=pd.to_datetime(d.DATE1.str.strip(),format='%d-%b-%Y')
  if not (internal==session).all(): raise ValueError('Raw file internal date mismatch')
  eq=b[(b.series=='EQ') & b['isin'].str.startswith('INE',na=False)].copy()
  duplicate=eq.duplicated(['date','symbol'],keep=False)
  bad_symbols=set(eq.loc[duplicate,'symbol'])
  eq=eq[~duplicate]
  piv=lambda col:eq.pivot(index='date',columns='symbol',values=col).reindex(dates)
  c,h,l,v,val=[piv(col) for col in ('close','high','low','volume','value')]
  # Research-only reproduction of membership, not certified effective-dated identity.
  monthend=dates[dates<session.replace(day=1)][-1]
  elig=(c.loc[monthend]>=50)&(c.notna().cumsum().shift(1).loc[monthend]>=252)
  medvalue=val.rolling(63,min_periods=63).median().loc[monthend]
  universe=medvalue[elig].dropna().sort_values(ascending=False).head(500).index.tolist()
  ca=pd.read_parquet(ca_path);ca['ex']=pd.to_datetime(ca.exDate,format='%d-%b-%Y',errors='coerce')
  # Exclude every recorded action, including dividends, rather than guessing factors.
  inwindow=ca[(ca.ex>=dates[max(0,i-320)])&(ca.ex<=session)]
  action_symbols=set(inwindow.symbol)
  raw_eq=d[d.SERIES.str.strip()=='EQ'].set_index('SYMBOL')
  daily_ret=c/c.shift(1)-1;relvol=v/v.shift(1).rolling(20,min_periods=20).median()
  high20=h.shift(1).rolling(20,min_periods=20).max();high252=h.shift(1).rolling(252,min_periods=252).max()
  sma50=c.rolling(50,min_periods=50).mean();sma200=c.rolling(200,min_periods=200).mean()
  prev=c.shift(1)
  tr=pd.DataFrame(np.maximum.reduce([(h-l).to_numpy(),(h-prev).abs().to_numpy(),(l-prev).abs().to_numpy()]),index=c.index,columns=c.columns)
  # Simple-mean ATR variant deliberately labeled; no claim of Wilder initialization.
  atr=tr.rolling(14,min_periods=14).mean()/c
  atrbase=atr.shift(1).rolling(63,min_periods=63).median()
  dd=c/c.rolling(20,min_periods=20).max()-1
  inputs={str(p.relative_to(ROOT)):sha(p) for p in paths+[ca_path,raw,ROOT/'ROADMAP.md']}
  config={'version':'r1-diagnostic-1','universe':'diagnostic Liquid-500 reproduction','membership_date':str(monthend.date()),'adjustment':'none; quarantine any recorded action in trailing 320 observed sessions','atr':'14-session simple mean true range / close','thresholds':{'gain':0.05,'relative_volume':2,'volatility_multiple':1.5,'drawdown':-0.10},'disabled':['sector_relative_strength','sector_breadth'],'production_eligible':False}
  signature=hashlib.sha256(json.dumps({'inputs':inputs,'config':config},sort_keys=True).encode()).hexdigest()[:12]
  batch=f'{session_s}_diagnostic_{signature}';run='routine_01_a01';target=R/f'runs/{batch}/routine_01/{run}'
  if target.exists():
   m=json.loads((target/'manifest.json').read_text());assert m['committed']
   for a in m['artifacts']:assert sha(target/a['path'])==a['sha256']
   print(json.dumps({'reused':True,'report':str(target/'report.md')}));return
  target.parent.mkdir(parents=True,exist_ok=True)
  tmp=Path(tempfile.mkdtemp(prefix='.pending_',dir=target.parent))
  metrics=[];findings=[];quarantine=[]
  ev=[{'evidence_id':'prices','source':str(paths[-1].relative_to(ROOT)),'source_document_hash':sha(paths[-1]),'source_type':'cached NSE-derived parquet','published_at':None,'retrieved_at':None,'retrieval_reason':'not recorded by this diagnostic','effective_session':session_s,'locator':'date/symbol/series columns','verification_status':'DIAGNOSTIC_ONLY'}, {'evidence_id':'raw','source':str(raw.relative_to(ROOT)),'source_document_hash':sha(raw),'source_type':'cached NSE bhavcopy CSV','published_at':None,'retrieved_at':None,'effective_session':session_s,'locator':'DATE1 and per-symbol row','verification_status':'INTERNAL_DATE_AND_PRICE_RECONCILED'}]
  for sym in universe:
   reasons=[]
   if sym in bad_symbols:reasons.append('DUPLICATE_IDENTITY')
   if sym in action_symbols:reasons.append('RECORDED_ACTION_IN_LOOKBACK')
   if sym not in raw_eq.index:reasons.append('MISSING_RAW_EQ')
   elif isinstance(raw_eq.loc[sym],pd.DataFrame):reasons.append('DUPLICATE_RAW_EQ')
   elif pd.notna(c.at[session,sym]) and abs(float(raw_eq.at[sym,'CLOSE_PRICE'])-c.at[session,sym])>0.011:reasons.append('RAW_PRICE_MISMATCH')
   if eq[eq.symbol==sym]['isin'].nunique()!=1:reasons.append('ISIN_CHANGED_IN_HISTORY')
   if not c[sym].iloc[max(0,i-320):i+1].notna().all():reasons.append('HISTORY_GAPS')
   values=[finite(x.at[session,sym]) for x in (c,h,l,v)]
   if any(x is None for x in values) or min(values)<=0 or not values[2]<=values[0]<=values[1]:reasons.append('INVALID_OHLCV')
   if reasons:quarantine.append({'symbol':sym,'reasons':sorted(set(reasons))});continue
   row={'symbol':sym,'security_id':str(eq[(eq.symbol==sym)&(eq.date==session)].iloc[0]['isin']),'session':session_s,'close_inr':finite(c.at[session,sym]),'return_pct':finite(daily_ret.at[session,sym]*100),'relative_volume':finite(relvol.at[session,sym]),'production_eligible':False,'evidence_refs':['prices','raw'],'calculation_version':config['version']}
   events=[]
   if daily_ret.at[session,sym]>.05 and relvol.at[session,sym]>2:events.append('PRICE_VOLUME_ANOMALY')
   for window,high in [(20,high20),(252,high252)]:
    if c.at[session,sym]>high.at[session,sym]:events.append(f'ABOVE_PRIOR_{window}_SESSION_HIGH')
   for window,ma in [(50,sma50),(200,sma200)]:
    if c.iloc[i-1][sym]<=ma.iloc[i-1][sym] and c.at[session,sym]>ma.at[session,sym]:events.append(f'CROSSED_ABOVE_SMA{window}')
   if atr.at[session,sym]>1.5*atrbase.at[session,sym]:events.append('VOLATILITY_EXPANSION_CONDITION')
   if dd.at[session,sym]<=-.1 and dd.iloc[i-1][sym]>-.1:events.append('DRAWDOWN_10PCT_CROSSING')
   row['events']=events;row['atr14_pct']=finite(atr.at[session,sym]*100);row['drawdown20_pct']=finite(dd.at[session,sym]*100)
   row['prior_high20_inr']=finite(high20.at[session,sym]);row['prior_high252_inr']=finite(high252.at[session,sym]);metrics.append(row)
   for event in events:
    findings.append({**row,'finding_id':hashlib.sha256(f'{signature}:{sym}:{event}'.encode()).hexdigest()[:20],'event_type':event,'priority':'P2','lifecycle':'BOOTSTRAP_OBSERVATION','observation_time':session_s+'T15:30:00+05:30','previous_value':None,'current_value':row['close_inr'],'units':'INR','materiality_rule':config['version'],'recipient':'routine_02','research_admissible':False})
  for name,records in [('signals.jsonl',findings),('metrics.jsonl',metrics),('quarantine.jsonl',quarantine),('evidence.jsonl',ev)]:
   (tmp/name).write_text(''.join(json.dumps(x,allow_nan=False)+'\n' for x in records))
  save(tmp/'config.json',config)
  ranked=sorted([m for m in metrics if m['events']],key=lambda x:(-len(x['events']),-x['relative_volume'],x['symbol']))
  limitations=['Phase 0 calendar, historical identity and corporate-action completeness are not certified.','Universe reproduction is diagnostic, not an approved membership snapshot.','Broad/sector relative strength and sector breadth are NOT_EVALUATED: benchmark readiness absent.','No previous committed R1 baseline: bootstrap, not claims of newly discovered signals.','Claude review NOT performed: shared metered-call budget accounting is not implemented.','Available data are dated 2026-10-09, not a live/current-session scan.']
  lines=[f'# Routine 1 diagnostic — {session_s}', '', '**Status: PARTIAL · production eligible: NO**', '', f'Owner: Codex. Reviewer: Claude — UNAVAILABLE (budget accounting absent). Run at {started}.', '',f'Universe: {len(universe)} diagnostic Liquid-500 names at {monthend.date()}; evaluated {len(metrics)}; quarantined {len(quarantine)}. Observed securities with events: {len(ranked)}; event records: {len(findings)}. Counts derive from [metrics](metrics.jsonl), [quarantine](quarantine.jsonl) and [signals](signals.jsonl).', '', '## Noteworthy diagnostic observations', '', '| Symbol | Events | Daily return | Volume / prior 20-session median |', '| --- | --- | --- | --- |']
  for x in ranked[:10]:lines.append(f"| {x['symbol']} | {', '.join(x['events'])} | {x['return_pct']:.2f}% | {x['relative_volume']:.2f}× |")
  lines+=['','All table metrics are as of '+session_s+'; [raw/evidence references](evidence.jsonl); [formula configuration](config.json). They are research observations, not validated opportunities.','','## Coverage and limitations','']+['- '+x for x in limitations]+['','## Next run','', 'Codex: certify calendar, effective identities, membership and corporate-action input completeness before promoting this lane. Add verified sector benchmarks and budget accounting. Claude: review signal interpretation when budget controls permit. Next R1 must load this diagnostic handoff and retain unresolved tasks; R2 may use these records as quarantined leads only, never qualification evidence.']
  (tmp/'report.md').write_text('\n'.join(lines)+'\n')
  artifacts=[{'path':p.name,'sha256':sha(p),'record_count':len(p.read_text().splitlines()) if p.suffix=='.jsonl' else None} for p in sorted(tmp.iterdir())]
  tasks=[{'task_id':'r1-'+code,'owner':owner,'security_id':None,'description':desc,'priority':'P1','status':'BLOCKED','created_run_id':run,'due_at':None,'trigger':'before production run','blocking_reason':desc,'evidence_refs':['ROADMAP.md']} for code,owner,desc in [('readiness','Codex','Certify applicable Phase 0 data gates'),('benchmarks','Codex','Verify benchmark/sector input series'),('budget','Codex','Implement shared metered-call accounting'),('review','Claude','Review diagnostic after budget readiness')]]
  hand={'schema_version':'1.1','routine_id':'routine_01','batch_id':batch,'run_id':run,'session_date':session_s,'started_at':started,'completed_at':datetime.now(TZ).isoformat(),'cutoff_at':session_s+'T15:30:00+05:30','timezone':'Asia/Kolkata','status':'PARTIAL','result':'CHANGED','execution_lane':'FAST','production_eligible':False,'readiness_ref':None,'budget_ref':None,'budget_usage':{'additional_model_calls':0,'external_fetches':0},'deferred_counts':{'phase0':len(quarantine),'benchmark_scans':2,'claude_review':1},'owner':'Codex','reviewer':'Claude','review_status':'UNAVAILABLE','previous_success_run_id':None,'supersedes_run_id':None,'bootstrap':True,'upstream_runs':[],'input_versions':inputs,'config_version':config['version'],'code_revision':{'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'scanner_sha256':sha(Path(__file__))},'coverage':{'expected':len(universe),'processed':len(metrics),'quarantined':len(quarantine)},'freshness':{'latest_cached_session':session_s,'live':False,'raw_internal_date_verified':True},'limitations':limitations,'artifacts':artifacts,'source_cursors':{},'processed_event_ids':[x['finding_id'] for x in findings],'open_tasks':tasks,'resolved_task_ids':[],'next_run':{'resume_from':batch+'/'+run,'allow_candidate_promotion':False,'instructions':'Retain these tasks; verify prerequisites; consume diagnostic signals only as quarantined leads.'}}
  save(tmp/'handoff.json',hand)
  manifest={'schema_version':'1.1','committed':True,'batch_id':batch,'run_id':run,'artifacts':artifacts+[{'path':'handoff.json','sha256':sha(tmp/'handoff.json'),'record_count':1}]}
  save(tmp/'manifest.json',manifest)
  for a in manifest['artifacts']:assert sha(tmp/a['path'])==a['sha256']
  assert len(metrics)+len(quarantine)==len(universe)
  os.rename(tmp,target)
  pointer=state/'latest.tmp';save(pointer,{'run_dir':str(target.relative_to(ROOT)),'status':'PARTIAL','production_eligible':False});os.replace(pointer,state/'latest.json')
  print(json.dumps({'report':str(target/'report.md'),'session':session_s,'universe':len(universe),'evaluated':len(metrics),'quarantined':len(quarantine),'securities_with_events':len(ranked),'events':len(findings),'top':[x['symbol'] for x in ranked[:5]],'status':'PARTIAL'}))

if __name__=='__main__':main()
