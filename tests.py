import unittest
import engine as e

DF = e.sample_data()
def ask(q):
    p = e.parse(q, DF)
    return p, (e.run(DF, p) if p else None)

class T(unittest.TestCase):
    def test_default_question_groups_by_product(self):
        p, o = ask("Show top 3 products by revenue for the last 30 days")
        self.assertEqual(p["group"], "product"); self.assertEqual(len(o["result"]), 3)
    def test_trend_is_chronological_line(self):
        p, o = ask("Show monthly revenue trend")
        self.assertEqual(p["chart"], "line"); l = list(o["result"]["label"]); self.assertEqual(l, sorted(l))
    def test_region_filter_applies(self):
        p, o = ask("revenue by product in North this month")
        self.assertEqual(p["filters"], {"region": "North"}); self.assertIn("region = 'North'", o["sql"])
    def test_hinglish(self):
        p, o = ask("is mahine sabse zyada kamai kaunsi cheez ki hui")
        self.assertEqual(p["period"], "this_month"); self.assertEqual(len(o["result"]), 1)
    def test_typos(self):
        p, _ = ask("revnue by regoin"); self.assertEqual(p["group"], "region")
    def test_bottom(self):
        p, o = ask("bottom 2 products by quantity")
        self.assertTrue(p["asc"]); self.assertLessEqual(o["result"]["value"].iloc[0], o["result"]["value"].iloc[1])
    def test_nonsense_not_understood(self):
        self.assertIsNone(e.parse("hello there", DF))
    def test_old_csv_last30_uses_data_date(self):
        import pandas as pd
        old = e.prepare_data(pd.DataFrame({"date": ["2024-01-01", "2024-01-20"], "product": ["A", "B"], "quantity": [1, 2], "revenue": [10, 40]}))
        p = e.parse("top products last 30 days", old); self.assertIsNotNone(e.run(old, p))
    def test_missing_columns_error(self):
        import pandas as pd
        with self.assertRaises(ValueError): e.prepare_data(pd.DataFrame({"a": [1]}))


import pandas as pd
def _two_weeks():
    rows = []
    for i in range(14):
        d = pd.Timestamp("2026-10-01") + pd.Timedelta(days=i)
        late = i >= 7
        rows += [(d, "Keyboard", "North", 1, 100 if late else 400), (d, "Notebook", "South", 1, 200 if late else 180)]
    return pd.DataFrame(rows, columns=["date", "product", "region", "quantity", "revenue"])

class Adv(unittest.TestCase):
    def test_drop_detected_and_changes_add_up(self):
        df = _two_weeks(); ins = e.insights(df)
        self.assertTrue(ins["ok"]); self.assertLess(ins["pct"], 0)
        self.assertIn("Keyboard", ins["points"][1])
        self.assertAlmostEqual(e.breakdown(df, "product")["change"].sum(), ins["current"] - ins["previous"])
    def test_short_data_is_handled(self):
        self.assertFalse(e.insights(_two_weeks().head(6))["ok"])
    def test_sample_data_digest_and_whatsapp(self):
        ins = e.insights(DF); self.assertTrue(ins["ok"]); self.assertGreaterEqual(len(ins["points"]), 3)
        self.assertIn("₹", e.whatsapp_summary(DF, shop="Test"))
    def test_anomaly_found(self):
        df = _two_weeks().copy(); df.loc[df.index[-1], "revenue"] = 9000
        self.assertTrue(e.anomalies(df, days=14, z=1.5))

if __name__ == "__main__": unittest.main(verbosity=1)
