import socket
import time
from datetime import datetime

import pandas as pd
import streamlit as st

# ---------- Page setup ----------
st.set_page_config(
    page_title="NetQoS Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Custom dark theme ----------
st.markdown("""
<style>
.stApp {
    background: radial-gradient(ellipse at top left,
        rgba(8,145,178,.16), transparent 40%), #070b14;
    color: #eaf3fb;
}
[data-testid="stSidebar"] {
    background: #0a1220;
    border-right: 1px solid #20364a;
}
.hero {
    padding: 28px;
    border-radius: 18px;
    border: 1px solid rgba(103,232,249,.3);
    background: linear-gradient(135deg,#102137,#09111e);
    box-shadow: 0 0 28px rgba(6,182,212,.08);
    margin-bottom: 22px;
}
.eyebrow {
    color: #67e8f9;
    letter-spacing: 3px;
    font-size: 12px;
    font-weight: bold;
}
div[data-testid="stMetric"] {
    background: #101d30;
    border: 1px solid #20364a;
    padding: 16px;
    border-radius: 14px;
}
div[data-testid="stMetricValue"] { color: #67e8f9; }
div.stButton > button, div.stDownloadButton > button {
    border-radius: 10px;
    border: 1px solid #38bdf8;
    transition: all .2s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    box-shadow: 0 0 18px rgba(103,232,249,.25);
    transform: translateY(-2px);
}
@keyframes glow {
    from { opacity: .55; }
    to { opacity: 1; }
}
.glow {
    color: #67e8f9;
    animation: glow 2s ease-in-out infinite alternate;
}
@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation: none !important;
        transition: none !important;
    }
}
</style>
""", unsafe_allow_html=True)

# ---------- Session history ----------
if "results" not in st.session_state:
    st.session_state.results = []


def test_tcp(host, port, timeout):
    """Measure TCP connection time from the app server."""
    started = time.perf_counter()
    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    try:
        with socket.create_connection(
            (host, port), timeout=timeout
        ):
            elapsed = (time.perf_counter() - started) * 1000

        return {
            "Time": timestamp,
            "Host": host,
            "Port": port,
            "Status": "Success",
            "Connect time (ms)": round(elapsed, 2),
            "Error": "",
        }

    except (socket.timeout, TimeoutError):
        elapsed = (time.perf_counter() - started) * 1000
        return {
            "Time": timestamp,
            "Host": host,
            "Port": port,
            "Status": "Timeout",
            "Connect time (ms)": round(elapsed, 2),
            "Error": f"Timed out after {timeout}s",
        }

    except OSError as exc:
        elapsed = (time.perf_counter() - started) * 1000
        return {
            "Time": timestamp,
            "Host": host,
            "Port": port,
            "Status": "Failed",
            "Connect time (ms)": round(elapsed, 2),
            "Error": str(exc)[:150],
        }


def parse_hosts(text):
    hosts = []
    errors = []

    for number, line in enumerate(text.splitlines(), 1):
        item = line.strip()

        if not item or item.startswith("#"):
            continue

        try:
            if "://" in item or "/" in item or " " in item:
                raise ValueError(
                    "Enter a hostname, not a URL."
                )

            if item.count(":") > 1:
                raise ValueError(
                    "IPv6 input is not supported here."
                )

            if ":" in item:
                host, port_text = item.rsplit(":", 1)
                port = int(port_text)
            else:
                host, port = item, 443

            if not host or not 1 <= port <= 65535:
                raise ValueError("Invalid host or port.")

            hosts.append((host, port))

        except ValueError as exc:
            errors.append(f"Line {number}: {exc}")

    return list(dict.fromkeys(hosts)), errors


# ---------- Sidebar ----------
with st.sidebar:
    st.markdown("## 📡 NetQoS Monitor")
    page = st.radio(
        "Navigation",
        ["Dashboard", "Diagnostics", "History & Reports", "About"],
    )

    st.divider()

    timeout = st.slider(
        "Connection timeout (seconds)",
        min_value=1.0,
        max_value=10.0,
        value=3.0,
        step=0.5,
    )

    threshold = st.number_input(
        "Slow connection threshold (ms)",
        min_value=1,
        max_value=10000,
        value=250,
        step=25,
    )

    if st.button("Clear session history"):
        st.session_state.results = []
        st.rerun()


# ---------- Header ----------
st.markdown("""
<div class="hero">
    <div class="eyebrow">NETWORK OBSERVABILITY</div>
    <h1>NetQoS <span style="color:#67e8f9">Monitor</span></h1>
    <p>TCP diagnostics, connection-time analytics and reports.</p>
    <span class="glow">● Monitoring workspace</span>
</div>
""", unsafe_allow_html=True)

st.info(
    "Tests run from the server hosting this app, not directly "
    "from your laptop or Wi-Fi. These are TCP connection checks, "
    "not ICMP ping tests."
)

history = pd.DataFrame(st.session_state.results)

if history.empty:
    history = pd.DataFrame(columns=[
        "Time", "Host", "Port", "Status",
        "Connect time (ms)", "Error"
    ])

success = history[history["Status"] == "Success"]
total = len(history)
success_count = len(success)
failure_count = total - success_count
success_rate = success_count / total * 100 if total else 0
average = (
    success["Connect time (ms)"].mean()
    if success_count else None
)

# ---------- Dashboard ----------
if page == "Dashboard":
    st.subheader("Performance overview")

    a, b, c, d = st.columns(4)
    a.metric("Total checks", total)
    b.metric("Success rate", f"{success_rate:.1f}%")
    c.metric(
        "Average TCP time",
        f"{average:.2f} ms" if average is not None else "—",
    )
    d.metric("Failures", failure_count)

    left, right = st.columns(2)

    with left:
        st.markdown("### Connection-time trend")

        if success_count:
            chart = success.copy()
            chart["Time"] = pd.to_datetime(
                chart["Time"], errors="coerce"
            )
            chart = chart.dropna(subset=["Time"])
            chart = chart.sort_values("Time")

            if not chart.empty:
                st.line_chart(
                    chart.set_index("Time")["Connect time (ms)"]
                )
        else:
            st.caption(
                "Run diagnostics to see connection-time trends."
            )

    with right:
        st.markdown("### Check status")

        if total:
            st.bar_chart(history["Status"].value_counts())
        else:
            st.caption("No test results yet.")

    st.markdown("### Recent results")

    if total:
        st.dataframe(
            history.tail(10).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write("Open Diagnostics to run your first test.")


# ---------- Diagnostics ----------
elif page == "Diagnostics":
    st.subheader("TCP connectivity diagnostics")

    raw_hosts = st.text_area(
        "Hosts — enter one per line",
        value="example.com:443\ngithub.com:443\nstreamlit.io:443",
        height=130,
        help="You can enter hostname:port or hostname alone. "
             "Port 443 is used when no port is specified.",
    )

    hosts, errors = parse_hosts(raw_hosts)

    for error in errors:
        st.warning(error)

    st.caption(
        f"{len(hosts)} valid unique target(s). "
        "Maximum 20 targets per run."
    )

    if st.button(
        "▶ Run diagnostics",
        type="primary",
        disabled=not hosts,
    ):
        if len(hosts) > 20:
            st.error("Please test no more than 20 hosts per run.")
        else:
            progress = st.progress(0)
            new_results = []

            for i, (host, port) in enumerate(hosts, 1):
                progress.progress(
                    (i - 1) / len(hosts),
                    text=f"Testing {host}:{port}...",
                )

                result = test_tcp(host, port, timeout)
                new_results.append(result)

                progress.progress(i / len(hosts))

            st.session_state.results.extend(new_results)
            progress.empty()
            st.success(f"Completed {len(new_results)} checks.")
            st.rerun()

    if total:
        st.markdown("### Results")
        st.dataframe(
            history.tail(max(1, len(hosts))).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )

        slow = success[
            success["Connect time (ms)"] >= threshold
        ]

        if failure_count:
            st.warning(
                f"{failure_count} failed or timed-out checks "
                "are in your session history."
            )

        if len(slow):
            st.warning(
                f"{len(slow)} successful connection(s) met or "
                f"exceeded the {threshold} ms threshold."
            )


# ---------- Reports ----------
elif page == "History & Reports":
    st.subheader("History & reports")

    if history.empty:
        st.info(
            "No history yet. Run diagnostics first. "
            "History is temporary and may reset when the app restarts."
        )
    else:
        selected_hosts = st.multiselect(
            "Filter by host",
            sorted(history["Host"].unique()),
            default=sorted(history["Host"].unique()),
        )

        selected_status = st.multiselect(
            "Filter by status",
            sorted(history["Status"].unique()),
            default=sorted(history["Status"].unique()),
        )

        filtered = history[
            history["Host"].isin(selected_hosts)
            & history["Status"].isin(selected_status)
        ]

        st.dataframe(
            filtered.iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇ Download filtered CSV",
            data=filtered.to_csv(index=False).encode("utf-8"),
            file_name="netqos_filtered_report.csv",
            mime="text/csv",
        )

        st.download_button(
            "⬇ Download all history CSV",
            data=history.to_csv(index=False).encode("utf-8"),
            file_name="netqos_history.csv",
            mime="text/csv",
        )


# ---------- About ----------
else:
    st.subheader("About NetQoS Monitor")

    st.markdown("""
NetQoS Monitor is a learning project for network diagnostics
and basic connection-performance reporting.

**Features**
- TCP connection tests for hosts and ports
- Connection time measured in milliseconds
- Success, timeout and failure status
- Connection-time charts and summary metrics
- Filterable history and CSV downloads
- Configurable slow-connection threshold

**Important measurement notes**
- TCP connection time is measured from the app server.
- It is not ICMP ping, packet loss, or a direct measurement
  of your laptop's Wi-Fi.
- History is stored in session memory and may reset.
- A successful TCP connection does not guarantee that the
  entire website or service is healthy.
""")

    st.markdown("**Built with:** Python · Streamlit · pandas")

st.divider()
st.caption(
    "NetQoS Monitor · Educational diagnostics tool · "
    "Only test systems you are authorized to assess."
)
