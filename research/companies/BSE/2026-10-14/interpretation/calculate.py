"""Reproducible interpretation model; all forward inputs are SCENARIO ASSUMPTION.
Run: python calculate.py. INR crore, except per-share INR and percentages.
Original model and evidence are read only. No trading operations.
"""
import json, math
from pathlib import Path
R=Path(__file__).resolve().parent
original=json.loads((R.parent/'model-output.json').read_text())
history=[{'year':f'FY{y}','total_income':inc,'source':'S3 PDF29','classification':'VERIFIED','basis':'company presentation rounded total income incl investment/other income'} for y,inc in zip(range(21,27),[654.7,863.5,953.9,1596.0,3236.3,5148.1])]
for i,h in enumerate(history): h['growth_pct']=None if i==0 else 100*(h['total_income']/history[i-1]['total_income']-1)
# Base is the annualised June2026 quarter, NOT a reported FY27 forecast.
base={'derivatives_revenue':4620.0,'other_operating_revenue':1644.08,'opex_cash':2080.0,'depreciation':170.4,'investment_income':540.72,'other_nonoperating':22.08,'associate_profit_after_tax':78.16,'shares_crore':41.1979077,'price':3375.4}
# Decompose expense using the management rounded 54% variable-cost disclosure.
# This includes Core SGF in cash operating expenses; no second SGF expense charge.
variable_rate=(2080*.54)/6264.08
fixed_base=2080*.46
cases={
 'Bear':dict(industry=.00,relative_share=-.05,yield_change=-.03,other_growth=.04,fixed_cost_growth=.08,variable_rate=variable_rate+.025,da_growth=.08,investment_growth=-.05,associate_growth=.00,tax=.27,capex_rate=.10,wc_rate=.05,reserve_rate=.03,dilution=.01,pe=25,payout=.25),
 'Base':dict(industry=.10,relative_share=.03,yield_change=.00,other_growth=.10,fixed_cost_growth=.08,variable_rate=variable_rate,da_growth=.08,investment_growth=.00,associate_growth=.05,tax=.25,capex_rate=.08,wc_rate=.03,reserve_rate=.02,dilution=.00,pe=35,payout=.25),
 'Bull':dict(industry=.16,relative_share=.05,yield_change=.01,other_growth=.15,fixed_cost_growth=.10,variable_rate=variable_rate-.005,da_growth=.12,investment_growth=.03,associate_growth=.10,tax=.25,capex_rate=.07,wc_rate=.02,reserve_rate=.02,dilution=.00,pe=45,payout=.25)}
rows=[]
for name,c in cases.items():
 previous_revenue=6264.08; cumulative_dps=0
 for t in range(1,6):
  deriv=base['derivatives_revenue']*((1+c['industry'])*(1+c['relative_share'])*(1+c['yield_change']))**t
  other=base['other_operating_revenue']*(1+c['other_growth'])**t
  revenue=deriv+other; variable=revenue*c['variable_rate']; fixed=fixed_base*(1+c['fixed_cost_growth'])**t
  ebitda=revenue-variable-fixed; da=base['depreciation']*(1+c['da_growth'])**t
  investment=base['investment_income']*(1+c['investment_growth'])**t
  nonop=base['other_nonoperating']; assoc=base['associate_profit_after_tax']*(1+c['associate_growth'])**t
  pretax=ebitda-da+investment+nonop; tax=max(pretax,0)*c['tax']; pat=pretax-tax+assoc
  shares=base['shares_crore']*(1+c['dilution'])**t; eps=pat/shares
  capex=revenue*c['capex_rate']; wc=max(0,revenue-previous_revenue)*c['wc_rate']; reserve=revenue*c['reserve_rate']
  # Prudential proxy: no associate earnings paid out without demonstrated cash remittance.
  cash_proxy=pat-assoc+da-capex-wc-reserve
  dividend=min(max(pat,0)*c['payout'],max(cash_proxy,0)); dps=dividend/shares; cumulative_dps+=dps
  price=eps*c['pe']; wealth=price+cumulative_dps
  row=dict(case=name,year=t,derivatives_revenue=deriv,other_operating_revenue=other,revenue=revenue,variable_cost=variable,fixed_cost=fixed,ebitda=ebitda,ebitda_margin_pct=100*ebitda/revenue,depreciation=da,investment_income=investment,other_nonoperating=nonop,associate_after_tax=assoc,pretax_ex_associate=pretax,tax=tax,parent_pat=pat,shares_crore=shares,eps=eps,capex=capex,incremental_working_capital=wc,incremental_capital_reserve=reserve,cash_proxy=cash_proxy,dividend=dividend,dps=dps,cumulative_dps=cumulative_dps,pe=c['pe'],implied_price=price,terminal_wealth_with_dividends=wealth,price_return_pct=100*(price/base['price']-1),total_return_pct=100*(wealth/base['price']-1),price_cagr_pct=100*((price/base['price'])**(1/t)-1),wealth_cagr_pct=100*((wealth/base['price'])**(1/t)-1),classification='SCENARIO ASSUMPTION / CALCULATED')
  assert abs(row['parent_pat']-row['eps']*row['shares_crore'])<1e-8
  assert dividend<=max(cash_proxy,0)+1e-8
  assert abs(revenue-variable-fixed-ebitda)<1e-8
  rows.append(row); previous_revenue=revenue
# Aligned profitability calculation: exclude non-operating income; include SGF/regulatory expense.
peer={'bse_fy26_operating_margin':100*(3233.72-290.30-23.85+158.96+.16)/4833.95,
      'mcx_fy26_operating_margin':100*(1773.63-127.05)/2302,
      'bse_fy25_operating_margin':100*(1665.68-254.70-24.27+112.98+.03)/2957.34,
      'mcx_fy25_operating_margin':100*(761.51-96.20)/1112.66,
      'bse_fy26_roe_avg':100*2496.98/((4423.73+6673.01)/2),
      'bse_fy26_roa_avg':100*2487.25/((10341.65+13446.14)/2),
      'bse_fy26_receivable_days_ending':553.16/4833.95*365,
      'bse_fy25_receivable_days_ending':287.78/2957.34*365,
      'bse_fy26_tax_rate':100*823.84/3299.14,
      'mcx_fy26_revenue_growth':100*(2302/1112.66-1)}
out={'cutoff':'2026-10-14','base':base,'base_sources':'S2 PDF5; S3 PDF13; S4 variable expense narrative; S1 EPS share basis','assumptions':cases,'history':history,'history_cagr_5y_pct':100*((5148.1/654.7)**.2-1),'peer_metrics':peer,'scenarios':rows}
(R/'calculations.json').write_text(json.dumps(out,indent=2)+'\n')
# Static financial charts as SVG; every scale starts at zero, no dual axes.
def bars(filename,title,labels,values,unit,footer):
 width,height=1000,420; ymax=max(values)*1.18; left,bottom,top=95,320,70; step=820/len(values)
 svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="420" viewBox="0 0 1000 420"><rect width="1000" height="420" fill="#f8fafc"/><g font-family="Arial,sans-serif" fill="#172b4d"><text x="40" y="35" font-size="22" font-weight="bold">{title}</text><text x="40" y="58" font-size="13">{unit}</text>']
 for j in range(5):
  v=ymax*j/4; yy=bottom-(bottom-top)*j/4
  svg.append(f'<line x1="{left}" x2="930" y1="{yy}" y2="{yy}" stroke="#dbe3ed"/><text x="85" y="{yy+4}" text-anchor="end" font-size="12">{v:,.0f}</text>')
 for i,(label,v) in enumerate(zip(labels,values)):
  x=left+step*i+step*.2; h=v/ymax*(bottom-top)
  svg.append(f'<rect x="{x}" y="{bottom-h}" width="{step*.6}" height="{h}" rx="4" fill="#2563a6"/><text x="{x+step*.3}" y="{bottom-h-9}" text-anchor="middle" font-size="14">{v:,.0f}</text><text x="{x+step*.3}" y="345" text-anchor="middle" font-size="14">{label}</text>')
 svg.append(f'<text x="40" y="387" font-size="12">{footer}</text></g></svg>');(R/filename).write_text(''.join(svg))
bars('history.svg','BSE: six annual observations, FY21–FY26',[h['year'] for h in history],[h['total_income'] for h in history],'Total income, INR crore; includes investment and other income','Source: BSE Q1 FY27 presentation p29. Rounded series; not operating revenue.')
bars('scenario-prices.svg','BSE: conditional five-year price scenarios',[r['case'] for r in rows if r['year']==5],[r['implied_price'] for r in rows if r['year']==5],'INR per share; hypothetical outputs, not price targets','Source: calculate.py. Assumptions are analyst-selected; dividends excluded. Reference quote INR3,375.40.')
# Tables exported as Markdown to avoid hidden spreadsheet formula state.
lines=['# Growth and valuation scenarios','', '**SCENARIO ASSUMPTION / CALCULATED.** Baseline: annualised June2026 quarter. Horizons are 1, 3 and 5 years from the research date; results represent terminal annual earnings capacity, not named fiscal-year forecasts. No case probability or probability-weighted expected price is assigned.','', '| Case | Years | Revenue, crore | EBITDA margin | Parent profit, crore | EPS | P/E | Implied price | Cumulative dividends/share | Wealth incl dividends | Price CAGR | Wealth CAGR |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for r in rows:
 if r['year'] in (1,3,5): lines.append(f"| {r['case']} | {r['year']} | {r['revenue']:,.0f} | {r['ebitda_margin_pct']:.1f}% | {r['parent_pat']:,.0f} | {r['eps']:.2f} | {r['pe']}x | {r['implied_price']:,.0f} | {r['cumulative_dps']:.2f} | {r['terminal_wealth_with_dividends']:,.0f} | {r['price_cagr_pct']:.1f}% | {r['wealth_cagr_pct']:.1f}% |")
lines += ['', 'Wealth CAGR measures terminal price plus unreinvested cumulative cash dividends relative to the indicative INR3,375.40 starting quote. It is not a dividend-timing IRR. Excludes transaction costs and investor taxes. All prices inherit the unresolved official-price verification.','', '![Five-year scenarios](scenario-prices.svg)','', '## Annual assumptions','', '| Input | Bear | Base | Bull |','|---|---:|---:|---:|']
keys=[('industry','Industry premium activity'),('relative_share','BSE relative share change'),('yield_change','Net fee yield change'),('other_growth','Other operating revenue growth'),('fixed_cost_growth','Fixed cash-cost growth'),('variable_rate','Variable cost / revenue'),('da_growth','Depreciation growth'),('investment_growth','Investment-income growth'),('associate_growth','Associate profit growth'),('tax','Tax / pre-associate pre-tax profit'),('capex_rate','Cash capex / revenue'),('wc_rate','Working capital / positive revenue increase'),('reserve_rate','Additional capital reserve / revenue'),('dilution','Annual share dilution'),('payout','Maximum earnings payout')]
for k,label in keys: lines.append('| '+label+' | '+' | '.join(f'{cases[c][k]*100:.1f}%' for c in cases)+' |')
lines+=['','## Mechanics and limitations','', 'Derivatives revenue compounds industry activity × relative share × net fee yield. A 3% relative share gain means a 1.03 multiplier, not three percentage points of absolute share. Absolute current market share is not verified; the relative index must be checked against industry capacity before use as a forecast. Other operating revenue compounds independently.','', 'Revenue less variable expenses and fixed cash costs gives EBITDA; depreciation is deducted to obtain operating profit. Investment income and other non-operating income are added. Tax is applied before adding the already-after-tax share of associate profit. Non-controlling losses are set to zero for the scenarios. EPS divides parent profit by the assumed diluted share count.','', 'Cash available for the modelled dividend is conservatively proxied as parent profit minus associate profit plus depreciation minus capex, incremental working capital and additional capital reserve. Dividends are the lesser of 25% of positive profit and positive cash proxy. Capital reserve here means additional locked capital, not a second income-statement SGF expense. Cash capex and depreciation are separate.','', 'This is a transparent driver model, not an integrated balance-sheet forecast: it does not allocate assets by useful life, solve regulatory capital requirements, or earn incremental investment income on retained cash. Investment income follows the explicit scenario assumption. The cash proxy cannot establish legal distributability. Terminal P/E reflects all modelled earnings; no additional cash or CDSL valuation is added, avoiding double counting.','', 'The base case is an organising assumption, not management guidance or consensus. Management statements remain in the evidence appendix. No comparable dated analyst forecast set was retrieved. The historical operating-cost split is rounded and the margin outcome is calculated, not independently assumed. Full annual outputs, capital needs and dividends are in calculations.json.']
(R/'05-scenarios.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'history_cagr':out['history_cagr_5y_pct'],'peer':peer,'five_year':[{k:r[k] for k in ['case','revenue','eps','implied_price','cumulative_dps']} for r in rows if r['year']==5]},indent=2))
