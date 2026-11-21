"""Meaningful failure-boundary tests for the research overlay."""
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from budget import Budget, BudgetExceeded
from sources import validate_bhav
from pipeline import available_events, independent_results, monitor, screen_financial


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.b = Budget(Path(self.tmp.name) / 'budget.sqlite3')

    def tearDown(self):
        self.tmp.cleanup()

    def reserve(self, key='one', **kw):
        return self.b.reserve(key, 'batch', 'FAST', 'MODEL', 'claude',
                              input_tokens=20000, output_tokens=4000, usd=1.1, **kw)

    def test_unknown_cost_survives_restart_and_blocks_another_model(self):
        self.reserve()
        self.b.unknown('one', 'response timed out')
        restored = Budget(self.b.path)
        self.assertEqual(restored.snapshot()[0]['usd'], 1.1)
        with self.assertRaises(BudgetExceeded):
            restored.reserve('two', 'b', 'FAST', 'MODEL', 'claude', usd=.1)

    def test_reconciled_retry_never_replays_request(self):
        self.reserve()
        self.b.reconcile('one', usd=.05, input_tokens=100, output_tokens=50)
        with self.assertRaises(BudgetExceeded): self.reserve()
        self.reserve('two')

    def test_monthly_and_daily_critical_reserves_are_not_spendable(self):
        for i in range(3):
            self.reserve(str(i)); self.b.reconcile(str(i), usd=1.1)
        with self.assertRaises(BudgetExceeded): self.reserve('exhausted')

    def test_overrun_is_persisted_unknown_not_rolled_back(self):
        self.reserve()
        with self.assertRaises(BudgetExceeded): self.b.reconcile('one', usd=2)
        self.assertEqual(Budget(self.b.path).snapshot()[0]['state'], 'UNKNOWN')

    def test_batch_allowance_does_not_reset_at_midnight(self):
        for i in range(8):
            self.reserve(str(i), now=datetime.fromisoformat(f'2026-10-{i+1:02d}T23:00:00+05:30'))
            self.b.reconcile(str(i), usd=.01, input_tokens=1, output_tokens=1)
        with self.assertRaises(BudgetExceeded): self.reserve('ninth', now=datetime.fromisoformat('2026-10-09T00:01:00+05:30'))

    def test_holiday_reserved_previous_file_rejected(self):
        p = Path(self.tmp.name) / 'bhav.csv'
        p.write_text('SYMBOL,SERIES,DATE1\nABC,EQ,14-Oct-2026\n')
        with self.assertRaises(ValueError): validate_bhav(p, '2026-10-15')

    def test_overlap_ingestion_does_not_reset_or_double_charge_record_budget(self):
        self.assertEqual(self.b.admit_records('metadata', ['a','b'], 2), (['a','b'], []))
        restarted = Budget(self.b.path)
        self.assertEqual(restarted.admit_records('metadata', ['b','c'], 2), (['b'], ['c']))

    def test_future_publication_cannot_enter_discovery(self):
        cutoff = datetime.fromisoformat('2026-10-15T10:00:00+05:30')
        events = [{'seq_id': '1', 'an_dt': '15-Oct-2026 10:00:01'}, {'seq_id': '2', 'an_dt': None}]
        accepted, excluded = available_events(events, cutoff)
        self.assertFalse(accepted)
        self.assertEqual({e['reason'] for e in excluded}, {'AFTER_CUTOFF', 'PUBLICATION_TIME_UNKNOWN'})

    def test_fundamental_discovery_does_not_require_a_price_spike(self):
        event = {'symbol': 'ABC', 'sm_isin': 'INE000000001', 'seq_id': '1', 'published_at': '2026-10-14T18:00:00+05:30',
                 'desc': 'Outcome of Board Meeting', 'attchmntText': 'Financial results for the quarter', 'attchmntFile': 'https://example.invalid/result.pdf'}
        self.assertEqual(len(independent_results([event], {'ABC': 'INE000000001'})), 1)
        self.assertFalse(independent_results([event], {'ABC': 'INE000000002'}))

    def test_monitor_retains_original_forecast_and_initial_observation_is_not_confirmation(self):
        d = {'symbol': 'ABC', 'hypothesis': 'future profit growth', 'assumptions': [
            {'assumption_id': 'a', 'metric': 'pat_yoy_pct', 'operator': 'lt', 'threshold': 0}]}
        f = {'symbol': 'ABC', 'period_end': '2026-09-30', 'published_at': '2026-10-14T18:00:00+05:30',
             'metrics': {'pat': 105, 'prior_year_pat': 100}}
        now = datetime.fromisoformat('2026-10-15T10:00:00+05:30')
        baseline = monitor(d, f, None, now)
        self.assertEqual(baseline['checks'][0]['result'], 'BASELINE_ONLY')
        revised = {**d, 'assumptions': [{**d['assumptions'][0], 'threshold': 100}]}
        followup = monitor(revised, {**f, 'period_end': '2026-12-31'}, baseline, now)
        self.assertEqual(followup['checks'][0]['rule']['threshold'], 0)
        self.assertEqual(followup['checks'][0]['result'], 'NO_CHANGE')

    def test_insurance_uses_premium_and_underwriting_not_industrial_leverage(self):
        result = screen_financial({'symbol':'INSURER','basis':'INSURER_STATUTORY','period_end':'2026-09-30','evidence_id':'e',
            'metrics':{'pat':110,'prior_year_pat':100,'gross_written_premium':120,'prior_year_gross_written_premium':100,'combined_ratio_pct':107}})
        self.assertTrue(result['positive_pat_growth'])
        self.assertFalse(result['combined_ratio_below_100'])
        self.assertFalse(result['industrial_leverage_test_applied'])
        self.assertEqual(result['qualification'], 'NOT_EVALUATED')


if __name__ == '__main__': unittest.main()
