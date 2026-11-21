"""BSE research calculations. INR crore except EPS, share counts and ratios.

Run with Python 3. Outputs are sensitivities, not targets or recommendations.
Source IDs resolve through sources.json; each input retains its source location.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = {
    "FY25": {"revenue": 2957.34, "parent_pat": 1325.89, "continuing_group_pat": 1317.06, "cfo_continuing": 410.15, "capex": 153.23, "eps": 32.18, "source": "S1 printed pp153-154 (PDF164-165)"},
    "FY26": {"revenue": 4833.95, "parent_pat": 2496.98, "continuing_group_pat": 2475.30, "cfo_continuing": 3103.68, "capex": 515.16, "eps": 60.61, "source": "S1 printed pp153-154 (PDF164-165)"},
    "Q1FY26": {"revenue": 957.95, "parent_pat": 539.41, "group_pat": 538.17, "investment_income": 79.06, "eps": 13.09, "source": "S2 PDF5"},
    "Q4FY26": {"revenue": 1563.51, "parent_pat": 797.33, "group_pat": 795.47, "investment_income": 61.69, "eps": 19.35, "source": "S2 PDF5"},
    "Q1FY27": {"revenue": 1566.02, "parent_pat": 874.02, "group_pat": 872.66, "investment_income": 135.18, "eps": 21.22, "source": "S2 PDF5"},
}

def calculate():
    fy, old, q, prior = DATA['FY26'], DATA['FY25'], DATA['Q1FY27'], DATA['Q4FY26']
    growth = lambda a, b: 100 * (a / b - 1)
    # Cash flow denominator deliberately uses continuing GROUP profit, not parent PAT.
    metrics = {
        'fy26_revenue_growth_pct': growth(fy['revenue'], old['revenue']),
        'fy26_parent_pat_growth_pct': growth(fy['parent_pat'], old['parent_pat']),
        'q1_revenue_yoy_pct': growth(q['revenue'], DATA['Q1FY26']['revenue']),
        'q1_revenue_qoq_pct': growth(q['revenue'], prior['revenue']),
        'q1_parent_pat_yoy_pct': growth(q['parent_pat'], DATA['Q1FY26']['parent_pat']),
        'q1_parent_pat_qoq_pct': growth(q['parent_pat'], prior['parent_pat']),
        'investment_income_qoq_increase_crore': q['investment_income'] - prior['investment_income'],
        'ttm_eps_reported': fy['eps'] - DATA['Q1FY26']['eps'] + q['eps'],
        'ttm_parent_pat_crore': fy['parent_pat'] - DATA['Q1FY26']['parent_pat'] + q['parent_pat'],
        'q1_eps_times_four_NOT_forecast': q['eps'] * 4,
        'fy26_cfo_to_continuing_group_pat': fy['cfo_continuing']/fy['continuing_group_pat'],
        'fy25_cfo_to_continuing_group_pat': old['cfo_continuing']/old['continuing_group_pat'],
        'two_year_cfo_to_continuing_group_pat': (fy['cfo_continuing']+old['cfo_continuing'])/(fy['continuing_group_pat']+old['continuing_group_pat']),
        'fy26_cfo_less_capex_NOT_distributable_cash': fy['cfo_continuing']-fy['capex'],
        'fy25_cfo_less_capex_NOT_distributable_cash': old['cfo_continuing']-old['capex'],
        'fy26_other_liabilities_cashflow_contribution_crore': 727.67,
        'fy26_other_liabilities_contribution_pct_cfo': 100*727.67/fy['cfo_continuing'],
        'fy26_cfo_without_other_liabilities_increase_DIAGNOSTIC': fy['cfo_continuing']-727.67,
        'fy26_owned_bank_balances_ex_interest_crore': (6637+4667+151346+137461)/100,
        'fy26_contingent_claims_and_guarantees_crore': (13496+5930+13567+23)/100,
    }
    # Indicative quote: Upstox 13-Oct-2026 15:59 IST, checked against Kotak Neo.
    # Not verified against official NSE bhavcopy (download failed).
    price = 3375.40
    pe = price/metrics['ttm_eps_reported']
    metrics.update(indicative_price=price, indicative_ttm_pe=pe,
                   indicative_fy26_pe=price/fy['eps'],
                   indicative_annualized_q1_pe=price/(q['eps']*4))
    # Reverse expectations: required EPS CAGR to support an assumed price-return hurdle.
    # No forecast, assigned probability or recommended multiple. Dividends excluded.
    reverse = []
    for years in (3, 5):
        for terminal_pe in (25, 35, 45):
            reverse.append({'years': years, 'assumed_terminal_pe': terminal_pe,
                            'assumed_annual_price_return_pct': 12,
                            'required_eps_cagr_pct': 100*((pe*(1.12**years)/terminal_pe)**(1/years)-1)})
    # Earnings stress, indexed to 100: explicitly arbitrary operating assumptions.
    # Revenue-growth and margin cases are sensitivities, not analyst estimates.
    stress = []
    for label, rev_growth, margin in [('adverse',-.15,.50),('steady',.10,.64),('expansion',.25,.67)]:
        stress.append({'case':label,'assumed_revenue_growth_pct':rev_growth*100,
                       'assumed_operating_ebitda_margin_pct':margin*100,
                       'ebitda_index_vs_fy26_100':100*(1+rev_growth)*margin/(3078.7/4833.95)})
    return {'cutoff':'2026-10-14','inputs':DATA,'metrics':metrics,
            'reverse_expectations':reverse,'operating_sensitivities':stress,
            'limitations':['Indicative secondary-source price only','No EV or DCF: distributable cash unresolved','Rounded published EPS used for TTM','Sensitivity assumptions are not forecasts'],
            'extra_sources':{'cash_and_contingencies':'S1 notes 11,12,37','fy26_operating_ebitda':'S3 PDF26, INR million divided by 10','price':['https://upstox.com/stocks/bse-limited-share-price/','https://www.kotakneo.com/stocks/bse-share-price/']}}

if __name__ == '__main__':
    result = calculate()
    (ROOT/'model-output.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['metrics'],indent=2))
    print(json.dumps(result['reverse_expectations'],indent=2))
