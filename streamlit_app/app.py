import os
import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

st.set_page_config(page_title="Report Health Monitor", layout="wide")
cfg = Config()

@st.cache_data(ttl=60)
def q(query: str):
    with sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
        credentials_provider=lambda: cfg.authenticate,
    ) as conn, conn.cursor() as cur:
        cur.execute(query)
        return cur.fetchall_arrow().to_pandas()

st.title("Report Health Monitor")
tab1, tab2 = st.tabs(["Data health", "Business KPIs"])

with tab1:
    latest = q("""SELECT * FROM workspace.dq.dq_results
                  WHERE run_id = (SELECT run_id FROM workspace.dq.dq_results
                                  ORDER BY run_timestamp DESC LIMIT 1)""")
    c1, c2, c3 = st.columns(3)
    c1.metric("Checks run", len(latest))
    c2.metric("Failed", int((latest.status == "FAIL").sum()))
    c3.metric("Pass rate", f"{100*(latest.status=='PASS').mean():.1f}%")

    st.subheader("Pass-rate trend")
    trend = q("""SELECT run_timestamp,
        ROUND(100.0*SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END)/COUNT(*),1) AS pass_rate
        FROM workspace.dq.dq_results GROUP BY run_id, run_timestamp ORDER BY run_timestamp""")
    st.line_chart(trend, x="run_timestamp", y="pass_rate")

    st.subheader("Failing checks (latest run)")
    st.dataframe(latest[latest.status == "FAIL"], use_container_width=True)

with tab2:
    k = q("""SELECT ROUND(SUM(price),0) AS revenue, COUNT(DISTINCT order_id) AS orders,
                    ROUND(100.0*SUM(is_on_time)/SUM(is_delivered),1) AS on_time_pct
             FROM workspace.gold.fact_orders""").iloc[0]
    a, b, c = st.columns(3)
    a.metric("Revenue", f"{k.revenue:,.0f}")
    b.metric("Orders", f"{k.orders:,}")
    c.metric("On-time delivery %", f"{k.on_time_pct}%")