import socket
import time
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NetQoS Monitor",
    page_icon="📡",
    layout="wide"
)

COLUMNS = [
    "timestamp", "host", "port", "attempts", "successes",
    "failures", "success_rate", "avg_latency", "min_latency",
    "max_latency", "jitter", "status", "message"
]

if "results" not in st.session_state:
    st.session_state.results = pd.DataFrame(columns=COLUMNS)

if "alerts" not in st.session_state:
    st.session_state.alerts = []


def tcp_probe(host, port, timeout):
    start = time.perf_counter()

    try:
        with socket.create_connection(
            (host, port), timeout=timeout
        ):
            elapsed = (time.perf_counter() - start) * 1000

        return True, round(elapsed, 2), "Connection successful"

    except socket.gaierror:
        return False, None, "Hostname could not be resolved"

    except socket.timeout:
        return False, None, "Connection timed out"

    except OSError as error:
        return False, None, str(error)[:150]


def test_host(host, port, attempts, timeout):
    latencies = []
    errors = []
    successes = 0

    for _ in range(attempts):
        ok, latency, message = tcp_probe(
            host, port, timeout
        )

        if ok:
            successes += 1
            latencies.append(latency)
        else:
            errors.append(message)

        time.sleep(0.08)

    failures = attempts - successes
    success_rate = successes / attempts * 100

    avg_latency = (
        round(sum(latencies) / len(latencies), 2)
        if latencies else None
    )

    min_latency = min(latencies) if latencies else None
    max_latency = max(latencies) if latencies else None

    changes = [
        abs(latencies[i] - latencies[i - 1])
        for i in range(1, len(latencies))
    ]

    jitter = (
        round(sum(changes) / len(changes), 2)
        if changes else 0.0
    )

    if successes == attempts:
        status = "Healthy"
        message = "All probes succeeded"
    elif successes > 0:
        status = "Warning"
        message = errors[0] if errors else "Some probes failed"
    else:
        status = "Down"
        message = errors[0] if errors else "All probes failed"

    return {
        "timestamp": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
        "host": host,
        "port": port,
        "attempts": int(attempts),
        "successes": int(successes),
        "failures": int(failures),
        "success_rate": round(success_rate, 1),
        "avg_latency": avg_latency,
        "min_latency": min_latency,
        "max_latency": max_latency,
        "jitter": jitter,
        "status": status,
        "message": message
    }


def add_alerts(rows, latency_limit, jitter_limit):
    for row in rows:
        if row["status"] == "Down":
            st.session_state.alerts.append({
                "timestamp": row["timestamp"],
                "severity": "Critical",
                "host": row["host"],
                "message": "All connection attempts failed"
            })

        elif row["status"] == "Warning":
            st.session_state.alerts.append({
                "timestamp": row["timestamp"],
                "severity": "Warning",
                "host": row["host"],
                "message": "Some connection attempts failed"
            })

        if (
            row["avg_latency"] is not None
            and row["avg_latency"] > latency_limit
        ):
            st.session_state.alerts.append({
                "timestamp": row["timestamp"],
                "severity": "Warning",
                "host": row["host"],
                "message": "Latency exceeded the configured threshold"
            })

        if row["jitter"] > jitter_limit:
            st.session_state.alerts.append({
                "timestamp": row["timestamp"],
                "severity": "Warning",
                "host": row["host"],
                "message": "Latency variation exceeded the threshold"
            })

    st.session_state.alerts = st.session_state.alerts[-500:]


st.title("📡 NetQoS Monitor")
st.caption("Network Quality of Service Monitoring System")

st.info(
    "Tests run from the cloud server hosting this app, "
    "not directly from your laptop's Wi-Fi. "
    "TCP connection time is not the same as an ICMP ping."
)

with st.sidebar:
    st.header("⚙️ Test settings")

    host_text = st.text_area(
        "Hostnames (one per line)",
        value="google.com\ncloudflare.com",
        height=90
    )

    port = st.number_input(
        "TCP port",
        min_value=1,
        max_value=65535,
        value=443
    )

    attempts = st.slider(
        "Attempts per host", 1, 30, 10
    )

    timeout = st.slider(
        "Connection timeout (seconds)", 1, 10, 3
    )

    latency_limit = st.slider(
        "Latency alert threshold (ms)",
        10, 2000, 150, step=10
    )

    jitter_limit = st.slider(
        "Jitter alert threshold (ms)",
        1, 500, 30
    )

    run_test = st.button(
        "▶ Run live test",
        type="primary",
        use_container_width=True
    )

hosts = []

for line in host_text.splitlines():
    host = line.strip()

    if not host or host in hosts:
        continue

    if "://" in host or "/" in host or " " in host:
        st.sidebar.warning(f"Invalid hostname skipped: {host}")
    else:
        hosts.append(host)

dashboard, diagnostics, history, reports, about = st.tabs([
    "📊 Dashboard",
    "🩺 Diagnostics",
    "🕘 History",
    "📄 Reports",
    "ℹ️ About"
])

if run_test:
    if not hosts:
        st.error("Enter at least one valid hostname.")
    else:
        new_rows = []
        progress = st.progress(0)

        for index, host in enumerate(hosts):
            with st.spinner(f"Testing {host}:{int(port)}..."):
                row = test_host(
                    host,
                    int(port),
                    int(attempts),
                    float(timeout)
                )
                new_rows.append(row)

            progress.progress((index + 1) / len(hosts))

        progress.empty()

        new_df = pd.DataFrame(new_rows, columns=COLUMNS)

        st.session_state.results = pd.concat(
            [st.session_state.results, new_df],
            ignore_index=True
        )

        add_alerts(
            new_rows, latency_limit, jitter_limit
        )

        st.success("Network tests completed.")

df = st.session_state.results.copy()

if not df.empty:
    numeric_columns = [
        "attempts", "successes", "failures",
        "success_rate", "avg_latency", "min_latency",
        "max_latency", "jitter"
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(
            df[column], errors="coerce"
        )


with dashboard:
    st.subheader("Network dashboard")

    if df.empty:
        st.info(
            "Enter hostnames in the sidebar and click "
            "'Run live test' to collect results."
        )
    else:
        total_attempts = int(df["attempts"].fillna(0).sum())
        total_successes = int(df["successes"].fillna(0).sum())
        total_failures = int(df["failures"].fillna(0).sum())

        success_rate = (
            total_successes / total_attempts * 100
            if total_attempts else 0
        )

        valid_latency = df["avg_latency"].dropna()
        avg_latency = (
            valid_latency.mean()
            if not valid_latency.empty else None
        )

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Host tests", len(df))
        c2.metric("Success rate", f"{success_rate:.1f}%")
        c3.metric(
            "Average connection time",
            f"{avg_latency:.2f} ms"
            if avg_latency is not None else "N/A"
        )
        c4.metric("Failed probes", total_failures)

        c5, c6, c7 = st.columns(3)

        c5.metric("Successful probes", total_successes)

        valid_jitter = df["jitter"].dropna()
        avg_jitter = (
            valid_jitter.mean()
            if not valid_jitter.empty else None
        )

        c6.metric(
            "Latency variation",
            f"{avg_jitter:.2f} ms"
            if avg_jitter is not None else "N/A"
        )

        c7.metric(
            "Alerts recorded",
            len(st.session_state.alerts)
        )

        st.markdown("### Latest result per host")

        latest = df.drop_duplicates(
            subset=["host", "port"], keep="last"
        )

        st.dataframe(
            latest,
            use_container_width=True,
            hide_index=True
        )

        chart_df = df.dropna(subset=["avg_latency"])

        if not chart_df.empty:
            st.markdown("### Average TCP connection time")
            st.bar_chart(
                chart_df.set_index("timestamp")["avg_latency"]
            )

            st.markdown("### Success rate")
            st.line_chart(
                df.set_index("timestamp")["success_rate"]
            )

        st.markdown("### Alerts")

        alerts_df = pd.DataFrame(st.session_state.alerts)

        if alerts_df.empty:
            st.success("No alerts have been recorded.")
        else:
            st.dataframe(
                alerts_df.iloc[::-1],
                use_container_width=True,
                hide_index=True
            )


with diagnostics:
    st.subheader("Connection diagnostics")

    if df.empty:
        st.info("Run a live test first.")
    else:
        latest = df.drop_duplicates(
            subset=["host", "port"], keep="last"
        )

        for _, row in latest.iterrows():
            with st.expander(
                f"{row['host']}:{int(row['port'])} — {row['status']}"
            ):
                st.write("**Result:**", row["message"])
                st.write(
                    f"**Success rate:** {row['success_rate']:.1f}%"
                )

                if pd.notna(row["avg_latency"]):
                    st.write(
                        f"**Average TCP connection time:** "
                        f"{row['avg_latency']:.2f} ms"
                    )

                if row["status"] == "Down":
                    st.error(
                        "All attempts failed. Check the hostname, "
                        "port, DNS resolution, and service availability."
                    )
                elif row["status"] == "Warning":
                    st.warning(
                        "Some attempts failed. Run another test "
                        "and compare the results."
                    )
                else:
                    st.success(
                        "All probes succeeded in this test."
                    )


with history:
    st.subheader("Test history")

    if df.empty:
        st.info("No test history yet.")
    else:
        options = [
            "All hosts"
        ] + sorted(df["host"].dropna().unique().tolist())

        chosen_host = st.selectbox(
            "Filter by host", options
        )

        rows_to_show = st.selectbox(
            "Number of rows",
            ["10", "25", "50", "100", "All"]
        )

        filtered = df

        if chosen_host != "All hosts":
            filtered = filtered[
                filtered["host"] == chosen_host
            ]

        filtered = filtered.iloc[::-1]

        if rows_to_show != "All":
            filtered = filtered.head(int(rows_to_show))

        st.dataframe(
            filtered,
            use_container_width=True,
            hide_index=True
        )

        if st.button("Clear session history"):
            st.session_state.results = pd.DataFrame(
                columns=COLUMNS
            )
            st.session_state.alerts = []
            st.rerun()


with reports:
    st.subheader("Reports and CSV export")

    if df.empty:
        st.info("Run a test before generating a report.")
    else:
        summary = df.groupby(
            "host", as_index=False
        ).agg(
            tests=("host", "count"),
            attempts=("attempts", "sum"),
            successes=("successes", "sum"),
            failures=("failures", "sum"),
            mean_success_rate=("success_rate", "mean"),
            mean_latency_ms=("avg_latency", "mean"),
            mean_jitter_ms=("jitter", "mean")
        )

        st.markdown("### Summary by host")
        st.dataframe(
            summary.round(2),
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇ Download test history CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="netqos_history.csv",
            mime="text/csv"
        )

        alerts_df = pd.DataFrame(st.session_state.alerts)

        if not alerts_df.empty:
            st.markdown("### Alert report")

            st.dataframe(
                alerts_df,
                use_container_width=True,
                hide_index=True
            )

            st.download_button(
                "⬇ Download alerts CSV",
                data=alerts_df.to_csv(index=False).encode("utf-8"),
                file_name="netqos_alerts.csv",
                mime="text/csv"
            )


with about:
    st.subheader("About NetQoS Monitor")

    st.markdown("""
    **Purpose:** Monitor TCP connection availability and summarize
    connection-time measurements for selected hosts.

    **Features**
    - Multiple-host testing
    - Configurable port, attempt count, and timeout
    - Success and failure statistics
    - Average, minimum, and maximum connection times
    - Latency-variation proxy
    - Threshold-based alerts
    - Diagnostics and test history
    - CSV reports

    **Limitations**
    - Tests originate from the Streamlit cloud server, not directly
      from the visitor's laptop or Wi-Fi.
    - TCP connection time is not ICMP ping round-trip time.
    - The jitter value is a simple variation proxy, not a formal
      standards-based jitter measurement.
    - History is stored in session memory and may reset when the
      app or session restarts.
    """)

with st.sidebar:
    st.divider()
    st.caption("NetQoS Monitor • Student mini-project")
    st.caption(f"Rows in current session: {len(df)}")
