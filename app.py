import plotly.express as px
import streamlit as st
import pandas as pd
import engine as e

st.set_page_config(page_title="FlowInsights", page_icon="🎙️", layout="wide")
st.title("🎙️ FlowInsights")
st.caption("Speak or type a question about your sales. Get a chart, plus automatic insights. Works offline, no API key.")

with st.sidebar:
    st.header("Data")
    uploaded = st.file_uploader("Upload a sales CSV (optional)", type=["csv"])
    st.caption("Required columns: date, product, quantity, revenue. Optional: region, category.")
    shop = st.text_input("Shop / business name", "My shop")
    st.divider()
    st.header("What-if simulator")
    change_pct = st.slider("Assumed revenue change (%)", -50, 100, 10, 5)
    st.caption("Changes revenue mathematically. It is not a demand forecast.")

@st.cache_data
def load_sample(): return e.sample_data()

try:
    if uploaded is not None:
        df = e.prepare_data(pd.read_csv(uploaded)); st.success("Using your uploaded CSV. It is processed in memory only.")
    else:
        df = load_sample(); st.info("Using fictional sample sales data. Upload your own CSV from the sidebar.")
except Exception as exc:
    st.error(str(exc)); st.stop()

revenue, qty = float(df["revenue"].sum()), float(df["quantity"].sum())
c1, c2, c3 = st.columns(3)
c1.metric("Total revenue", f"₹{revenue:,.0f}"); c2.metric("Units sold", f"{qty:,.0f}"); c3.metric("Products", df["product"].nunique())

tab_ask, tab_ins = st.tabs(["🎙️ Ask a question", "💡 Auto insights"])

with tab_ask:
    st.write("Click the box, hold your **Wispr Flow** shortcut, speak, then press **Analyze**.")
    EXAMPLES = ["Top 3 products by revenue last 30 days", "Revenue by region", "Monthly revenue trend",
                "Which product sold the most units this week?", "Is mahine sabse zyada kamai kaunsi cheez ki hui?",
                "Pie chart of revenue by category"]
    if "q" not in st.session_state: st.session_state.q = EXAMPLES[0]
    cols = st.columns(3)
    for i, ex in enumerate(EXAMPLES):
        if cols[i % 3].button(ex, use_container_width=True): st.session_state.q = ex
    question = st.text_area("Question", key="q", height=80)
    if st.button("Analyze", type="primary"):
        plan = e.parse(question, df)
        out = e.run(df, plan) if plan else None
        if plan is None:
            st.warning("I couldn't understand that one. Try an example above, such as 'top 3 products by revenue last 30 days'.")
        elif out is None:
            st.info("No data matches that period or filter.")
        else:
            res = out["result"]
            st.subheader(out["explain"]); st.success(out["headline"])
            title = {"revenue": "Revenue (₹)", "quantity": "Units", "orders": "Orders"}[plan["metric"]]
            labels = {"label": plan["group"].capitalize(), "value": title}
            fig = (px.pie(res, names="label", values="value") if plan["chart"] == "pie" else
                   px.line(res, x="label", y="value", markers=True, labels=labels) if plan["chart"] == "line" else
                   px.bar(res, x="label", y="value", text_auto=".3s", labels=labels))
            st.plotly_chart(fig, use_container_width=True)
            show = res.rename(columns=labels)
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.download_button("Download results as CSV", show.to_csv(index=False).encode("utf-8"), "flowinsights_results.csv", "text/csv")
            with st.expander("How this was calculated (equivalent SQL)"):
                st.code(out["sql"], language="sql")
                st.caption("Built from fixed templates, so nothing a user types can run arbitrary code.")

with tab_ins:
    days = st.radio("Compare the latest", [7, 14, 30], horizontal=True, format_func=lambda d: f"{d} days vs the {d} before")
    ins = e.insights(df, days)
    if not ins["ok"]:
        st.info(ins["message"])
    else:
        a, b = st.columns(2)
        a.metric("Latest period revenue", f"₹{ins['current']:,.0f}", delta=f"{ins['pct']:+.0f}%")
        b.metric("Previous period revenue", f"₹{ins['previous']:,.0f}")
        for p in ins["points"]: st.markdown(f"- {p}")
        if ins["tip"]: st.warning("👉 " + ins["tip"])
        st.subheader("Why did it change?")
        st.caption("Change in revenue by product and by region (latest period minus previous). This shows what moved, not the cause.")
        d1, d2 = st.columns(2)
        for col, key in ((d1, "products"), (d2, "regions")):
            t = ins[key]; dim = t.columns[0]
            fig = px.bar(t, x=dim, y="change", color=(t["change"] >= 0).map({True: "Up", False: "Down"}),
                         color_discrete_map={"Up": "#2e9e5b", "Down": "#d64545"}, labels={"change": "Change (₹)"})
            fig.update_layout(showlegend=False)
            col.plotly_chart(fig, use_container_width=True)
        st.subheader("Share on WhatsApp")
        msg = e.whatsapp_summary(df, days, shop)
        st.text_area("Copy this message", msg, height=190)
        st.download_button("Download as .txt", msg.encode("utf-8"), "flowinsights_summary.txt", "text/plain")

st.divider()
st.subheader("What-if scenario")
a, b = st.columns(2)
a.metric("Current revenue", f"₹{revenue:,.0f}")
b.metric("Simulated revenue", f"₹{revenue * (1 + change_pct / 100):,.0f}", delta=f"{change_pct:+d}%")
st.caption("Illustrative only, not a prediction. Sample data is fictional; verify results before business decisions.")
