import socket
import time
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NetQoS Monitor",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -------------------- PROFESSIONAL DARK THEME --------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

:root {
    --bg: #070b13;
    --panel: #101b2b;
    --cyan: #67e8f9;
    --text: #edf6ff;
    --muted: #9aacc0;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    color: var(--text);
    background:
        radial-gradient(ellipse at 10% 0%, #102b3a 0%, transparent 35%),
        #070b13;
}

/* Reduce the space above the dashboard */
header[data-testid="stHeader"] {
    height: 0;
    visibility: hidden;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #101b2b, #080e18);
    border-right: 1px solid #24374a;
}

.block-container {
    max-width: 1450px;
    padding-top: 0.5rem !important;
    padding-bottom: 3rem;
}

h1, h2, h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.03em;
}

.hero {
    padding: 30px;
    margin-bottom: 24px;
    border-radius: 22px;
    border: 1px solid #285064;
    background: linear-gradient(120deg, #112639, #0b1320);
    box-shadow: 0 12px 40px #0005;
    animation: fadeIn .6s ease-out;
}

.eyebrow {
    color: var(--cyan);
    font-size: .75rem;
    font-weight: 700;
    letter-spacing: .16em;
    text-transform: uppercase;
}

.hero h1 {
    font-size: clamp(2rem, 4vw, 3.2rem);
    margin: 12px 0;
}

.hero p {
    color: var(--muted);
    font-size: 1rem;
}

.section-label {
    color: var(--cyan);
    font-size: .76rem;
    font-weight: 700;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin: 25px 0 12px;
}

div[data-testid="stMetric"] {
    background: linear-gradient(145deg, #142438, #0c1522);
    border: 1px solid #263c50;
    border-radius: 16px;
    padding: 18px;
    transition: transform .2s ease, border-color .2s ease;
}

div[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    border-color: var(--cyan);
}

div[data-testid="stMetricLabel"] {
    color: var(--muted);
}

div[data-testid="stMetricValue"] {
    color: var(--text);
    font-family: 'Space Grotesk', sans-serif;
}

.stButton > button,
.stDownloadButton > button {
    min-height: 44px;
    border-radius: 11px;
    border: 1px solid #397087;
    font-weight: 600;
    transition: all .2s ease;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(100deg, #67e8f9, #22d3ee);
    color: #06121c;
    border: none;
    box-shadow: 0 4px 22px #22d3ee22;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: var(--cyan);
    box-shadow: 0 0 18px #22d3ee25;
}

.stTextArea textarea,
.stTextInput input {
    background: #0b1625;
    border-color: #2b4258;
    border-radius: 10px;
}

[data-testid="stDataFrame"] {
    border: 1px solid #263c50;
    border-radius: 12px;
    overflow: hidden;
}

hr {
    border-color: #263747;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        animation: none !important;
        transition: none !important;
    }
}
</style>
""", unsafe_allow_html=True)


# -------------------- SESSION HISTORY --------------------
if "results" not in st.session_state:
    st.session_state.results = []

if "last_batch_size" not in st.session_state:
    st.session_state.last_batch_size = 10


# -------------------- NETWORK FUNCTIONS --------------------
def parse_hosts(raw):
    hosts = []
    errors = []

    for line_no, line in enumerate(raw.splitlines(), 1):
        item = line.strip()

        if not item or item.startswith("#"):
            continue

        try:
            if "://" in item or "/" in item or any(c.isspace() for c in item):
                raise ValueError(
                    "Enter a hostname or hostname:port, not a URL."
                )

            if item.count(":") > 1:
                raise ValueError("Use hostname:port format.")

            if ":" in item:
                host, port_text = item.rsplit(":", 1)
                port = int(port_text)
            else:
                host, port = item, 443

            if not host or not 1 <= port <= 65535:
                raise ValueError("Port must be between 1 and 65535.")

            hosts.append((host, port))

        except ValueError as exc:
            errors.append(f"Line {line_no}: {exc}")

    return list(dict.fromkeys(hosts)), errors


def tcp_probe(host, port, timeout):
    timestamp = datetime.now().astimezone().isoformat(
        timespec="seconds"
    )
    started = time.perf_counter()

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
            "Details": "",
        }

    except (socket.timeout, TimeoutError):
        elapsed = (time.perf_counter() - started) * 1000

        return {
            "Time": timestamp,
            "Host": host,
            "Port": port,
            "Status": "Timeout",
            "Connect time (ms)": round(elapsed, 2),
            "Details": f"Timed out after {timeout:.1f} seconds",
        }

    except OSError as exc:
        elapsed = (time.perf_counter() - started) * 1000

        return {
            "Time": timestamp,
            "Host": host,
            "Port": port,
            "Status": "Failed",
            "Connect time (ms)": round(elapsed, 2),
            "Details": str(exc)[:160],
        }


def section(title):
    st.markdown(
        f'<div class="section-label">{title}</div>',
        unsafe_allow_html=True,
    )


# -------------------- SIDEBAR --------------------
with st.sidebar:
    st.markdown(
        '<h2 style="color:#67e8f9">📡 NETQOS</h2>'
        '<p style="margin-top:-12px">NETWORK MONITOR</p>',
        unsafe_allow_html=True,
    )

    page = st.radio(
        "Navigation",
        ["Dashboard", "Diagnostics", "History & Reports", "About"],
    )

    st.divider()
    st.markdown("### Test settings")

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

    st.caption("Thresholds are configurable indicators.")

    if st.button("Clear session history", use_container_width=True):
        st.session_state.results = []
        st.session_state.last_batch_size = 10
        st.rerun()

    st.divider()
    st.caption("Network diagnostics for learning and demonstration.")


# -------------------- PREPARE DATA --------------------
columns = [
    "Time",
    "Host",
    "Port",
    "Status",
    "Connect time (ms)",
    "Details",
]

df = pd.DataFrame(st.session_state.results, columns=columns)
success_df = df[df["Status"] == "Success"]

total = len(df)
success_count = len(success_df)
failed_count = total - success_count

success_rate = success_count / total * 100 if total else 0

average_time = (
    success_df["Connect time (ms)"].mean()
    if success_count else None
)


# -------------------- HERO HEADER --------------------
st.markdown("""
<div class="hero">
    <div class="eyebrow">Network intelligence · TCP diagnostics</div>
    <h1>See your network <span style="color:#67e8f9">clearly.</span></h1>
    <p>
        Test endpoint reachability, measure TCP connection times,
        and review your results in one clean dashboard.
    </p>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Important: tests run from the Streamlit hosting server, "
    "not directly from your laptop or local Wi-Fi. "
    "TCP connection time is not the same as ICMP ping."
)


# -------------------- DASHBOARD --------------------
if page == "Dashboard":
    section("Network overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Total checks", f"{total:,}")
    c2.metric("Success rate", f"{success_rate:.1f}%")
    c3.metric(
        "Average TCP time",
        f"{average_time:.2f} ms" if average_time is not None else "—",
    )
    c4.metric("Failed checks", f"{failed_count:,}")

    chart_col, status_col = st.columns([1.5, 1])

    with chart_col:
        section("Connection performance")

        if success_count:
            chart_df = success_df.copy()
            chart_df["Time"] = pd.to_datetime(
                chart_df["Time"], errors="coerce"
            )
            chart_df = chart_df.dropna(subset=["Time"])
            chart_df = chart_df.sort_values("Time")

            if not chart_df.empty:
                st.line_chart(
                    chart_df.set_index("Time")["Connect time (ms)"],
                    height=280,
                )
        else:
            st.info(
                "Your performance chart will appear "
                "after you run your first test."
            )

    with status_col:
        section("Connection status")

        if total:
            st.bar_chart(
                df["Status"].value_counts(),
                height=280,
            )
        else:
            st.info("Run diagnostics to see your results here.")

    section("Recent activity")

    if total:
        st.dataframe(
            df.tail(10).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.write(
            "Choose **Diagnostics** in the sidebar "
            "to test your first endpoint."
        )


# -------------------- DIAGNOSTICS --------------------
elif page == "Diagnostics":
    section("Test your endpoints")

    st.write(
        "Enter one hostname per line. You can specify a port "
        "with `hostname:port`. If you omit the port, 443 is used."
    )

    raw_hosts = st.text_area(
        "Target endpoints",
        value="example.com:443\ngithub.com:443\nstreamlit.io:443",
        height=130,
        label_visibility="collapsed",
    )

    hosts, errors = parse_hosts(raw_hosts)

    for error in errors:
        st.warning(error)

    left, right = st.columns([1, 2])

    with left:
        st.metric("Valid targets", len(hosts))

    with right:
        st.caption(
            "Maximum 20 targets per run. Only test systems "
            "you are authorized to assess."
        )

    run_test = st.button(
        "▶ Run Live Test",
        type="primary",
        use_container_width=True,
        disabled=not hosts,
    )

    if run_test:
        if len(hosts) > 20:
            st.error("Please enter no more than 20 targets.")
        else:
            progress = st.progress(0)
            new_results = []

            for index, (host, port) in enumerate(hosts, start=1):
                progress.progress(
                    (index - 1) / len(hosts),
                    text=f"Testing {host}:{port}",
                )

                new_results.append(tcp_probe(host, port, timeout))

                progress.progress(
                    index / len(hosts),
                    text=f"Completed {index} of {len(hosts)}",
                )

            st.session_state.results.extend(new_results)
            st.session_state.last_batch_size = len(new_results)

            progress.empty()
            st.success(f"Completed {len(new_results)} TCP checks.")
            st.rerun()

    if total:
        section("Test results")

        batch_size = st.session_state.last_batch_size
        st.dataframe(
            df.tail(batch_size).iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )

        slow_df = success_df[
            success_df["Connect time (ms)"] >= threshold
        ]

        if failed_count:
            st.warning(
                f"{failed_count} failed or timed-out check(s) "
                "exist in the session history."
            )

        if len(slow_df):
            st.warning(
                f"{len(slow_df)} successful connection(s) "
                f"met or exceeded the {threshold} ms threshold."
            )


# -------------------- HISTORY AND REPORTS --------------------
elif page == "History & Reports":
    section("History and reports")

    if df.empty:
        st.info(
            "No test records yet. Run diagnostics first. "
            "Session history may reset when the app restarts."
        )

    else:
        col1, col2 = st.columns(2)

        with col1:
            selected_hosts = st.multiselect(
                "Filter by host",
                options=sorted(df["Host"].unique()),
                default=sorted(df["Host"].unique()),
            )

        with col2:
            selected_statuses = st.multiselect(
                "Filter by status",
                options=sorted(df["Status"].unique()),
                default=sorted(df["Status"].unique()),
            )

        filtered = df[
            df["Host"].isin(selected_hosts)
            & df["Status"].isin(selected_statuses)
        ]

        st.caption(f"Showing {len(filtered)} of {len(df)} records.")

        st.dataframe(
            filtered.iloc[::-1],
            use_container_width=True,
            hide_index=True,
        )

        d1, d2 = st.columns(2)

        with d1:
            st.download_button(
                "⬇ Download filtered CSV",
                data=filtered.to_csv(index=False).encode("utf-8"),
                file_name="netqos_filtered.csv",
                mime="text/csv",
                use_container_width=True,
            )

        with d2:
            st.download_button(
                "⬇ Download all CSV",
                data=df.to_csv(index=False).encode("utf-8"),
                file_name="netqos_history.csv",
                mime="text/csv",
                use_container_width=True,
            )


# -------------------- ABOUT --------------------
elif page == "About":
    section("About NetQoS Monitor")

    st.write(
        "NetQoS Monitor is an educational network diagnostics "
        "dashboard for checking TCP endpoint reachability "
        "and reviewing connection-time measurements."
    )

    left, right = st.columns(2)

    with left:
        st.subheader("Features")
        st.markdown("""
        - TCP connectivity testing
        - Success, failure and timeout reporting
        - Connection-time charts
        - Configurable slow-connection threshold
        - Filterable history
        - CSV report downloads
        """)

    with right:
        st.subheader("Technical notes")
        st.markdown("""
        - Tests originate from the hosting server
        - TCP connection time is not ICMP ping
        - This does not directly measure local Wi-Fi
        - History is temporary session data
        - TCP reachability does not guarantee application health
        """)

    st.markdown("**Built with:** Python · Streamlit · pandas")


# -------------------- FOOTER --------------------
st.divider()

st.caption(
    "NETQOS MONITOR  ·  Network diagnostics for learning and demonstration"
)
