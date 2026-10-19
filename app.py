import streamlit as st
import socket
import time
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="NetQoS Monitor", page_icon="📡", layout="wide")

st.markdown("""
<style>
.stApp {background:#08111f;color:#e8f1ff}
[data-testid="stMetric"] {
 background:#12243a;padding:16px;border-radius:12px;
 border:1px solid #203d5c
}
[data-testid="stMetricValue"] {color:#48d8f0}
</style>
""", unsafe_allow_html=True)

st.title("📡 NetQoS Monitor")
st.caption("Network Quality of Service Monitoring System")

with st.sidebar:
    st.header("Test settings")
    host = st.text_input("Target hostname", "google.com")
    port = st.number_input("TCP port", 1, 65535, 443)
    count = st.slider("Number of tests", 3, 20, 10)
    run = st.button("Run live test")

if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame()

if run:
    records = []
    for i in range(count):
        start = time.perf_counter()
        try:
            with socket.create_connection(
                (host, int(port)), timeout=3
            ):
                latency = (time.perf_counter() - start) * 1000
                records.append({
                    "Probe": i + 1,
                    "Latency (ms)": round(latency, 2),
                    "Status": "Success"
                })
        except Exception:
            records.append({
                "Probe": i + 1,
                "Latency (ms)": None,
                "Status": "Failed"
            })
        time.sleep(0.1)

    st.session_state.results = pd.DataFrame(records)

df = st.session_state.results

if not df.empty:
    good = df.dropna(subset=["Latency (ms)"])
    success = (df["Status"] == "Success").sum()
    failed = len(df) - success
    avg = good["Latency (ms)"].mean() if not good.empty else 0
    jitter = (
        good["Latency (ms)"].diff().abs().dropna().mean()
        if len(good) > 1 else 0
    )
    rate = success / len(df) * 100
    score = max(0, min(100,
        100 - avg * 0.35 - jitter * 0.15
        - failed / len(df) * 50
    ))

    a, b, c, d, e = st.columns(5)
    a.metric("Avg Latency", f"{avg:.2f} ms")
    b.metric("Jitter Estimate", f"{jitter:.2f} ms")
    c.metric("Success Rate", f"{rate:.1f}%")
    d.metric("Failed Probes", int(failed))
    e.metric("Demo QoS Score", f"{score:.1f}/100")

    left, right = st.columns(2)
    with left:
        st.subheader("Latency Chart")
        if not good.empty:
            fig = px.line(
                good, x="Probe", y="Latency (ms)",
                markers=True, template="plotly_dark"
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Probe Status")
        fig = px.pie(
            df, names="Status", hole=0.55,
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Test Results")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        "netqos_results.csv",
        "text/csv"
    )

    if failed:
        st.warning("Some probes failed. Check the host or port.")
    else:
        st.success("All probes succeeded in this test run.")
else:
    st.info("Choose a target in the sidebar and click Run live test.")

with st.expander("About the measurements"):
    st.write("""
    TCP latency measures connection setup time, not ICMP ping RTT.
    Jitter is estimated from changes between successful samples.
    The QoS score is a custom illustrative score, not an official
    industry standard. Tests run from the hosting server, not directly
    from your computer or home Wi-Fi.
    """)
