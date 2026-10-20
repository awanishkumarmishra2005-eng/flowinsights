# FlowInsights

Speak a question about your sales data and get a chart, a headline and a table. Built for **No Hands: The Wispr Challenge**.

## Why
Small business owners lose hours turning sales data into answers because they cannot write SQL or build pivot tables. FlowInsights answers plain questions, including Hinglish ones, instantly.

## Features
- Works fully offline, **no API key**. Deterministic rules, so results are predictable.
- Questions like: top 3 products last 30 days, revenue by region, monthly trend (line chart), bottom 2 by quantity, revenue in North this month, Hinglish ("is mahine sabse zyada kamai kaunsi cheez ki hui").
- Handles typos, period words (today, this week, last month, last 30 days) and filters (region, product, category).
- Headline sentence, chart, table, CSV download, and the equivalent SQL for transparency.
- CSV upload (`date, product, quantity, revenue`; optional `region`, `category`). "Last 30 days" is based on the latest date in your data.
- **Auto insights:** compares the latest 7/14/30 days with the period before, and flags the biggest product drop and gain, the region that moved most, the best weekday and unusual days.
- **"Why did it change?"** drill-down charts by product and region. They show what moved, not the cause.
- **Shareable summary:** a WhatsApp-ready message you can copy or download.
- What-if revenue slider (not a forecast).

## Wispr Flow usage
Wispr Flow is desktop dictation. Click the question box, hold the Wispr shortcut, speak, and Wispr types the text. It is not embedded as an API. I also dictated my prompts, notes and this README while building.

## Run (Windows PowerShell)
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```
macOS/Linux: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && streamlit run app.py`

## Tests
`python tests.py` (13 tests: grouping, chronological trends, filters, Hinglish, typos, old CSV dates, bad CSV, insights, drill-down totals, anomalies, short data).

## Limits
Supports predefined question patterns, not any free-form question. Sample data is fictional.
