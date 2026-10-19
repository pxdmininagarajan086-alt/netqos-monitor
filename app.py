import socket
import time
import sqlite3
import statistics
from datetime import datetime

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NetQoS Monitor",
    page_icon="📡",
    layout="wide"
)

DB_PATH = "netqos_history.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tested_at TEXT,
                host TEXT,
                port INTEGER,
                attempts INTEGER,
                successes INTEGER,
                failures INTEGER,
                avg_latency REAL,
                min_latency REAL,
                max_latency REAL,
                jitter REAL,
                success_rate REAL,
                health_score REAL
            )
        """)


def save_result(result):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO history (
                tested_at, host, port, attempts, successes,
                failures, avg_latency, min_latency, max_latency,
                jitter, success_rate, health_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result["tested_at"], result["host"], result["port"],
            result["attempts"], result["successes"],
            result["failures"], result["avg_latency"],
            result["min_latency"], result["max_latency"],
            result["jitter"], result["success_rate"],
            result["health_score"]
        ))


def load_history():
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(
            "SELECT * FROM history ORDER BY id DESC",
            conn
        )


def valid_host(host):
    return (
        bool(host)
        and len(host) <= 253
        and "://" not in host
        and "/" not in host
        and not any(c.isspace() for c in host)
    )


def tcp_test(host, port, attempts, timeout):
    samples = []
    rows = []

    for number in range(attempts):
        start = time.perf_counter()
        error = ""

        try:
            with socket.create_connection(
                (host, port), timeout=timeout
            ):
                success = True
        except OSError as exc:
            success = False
            error = str(exc)

        elapsed = (time.perf_counter() - start) * 1000

        if success:
            samples.append(elapsed)

        rows.append({
            "Attempt": number + 1,
            "Status": "Success" if success else "Failed",
            "TCP connection time (ms)": round(elapsed, 2),
            "Error": error
        })

        if number < attempts - 1:
            time.sleep(0.15)

    successes = len(samples)
    failures = attempts - successes
    avg = statistics.mean(samples) if samples else None
    minimum = min(samples) if samples else None
    maximum = max(samples) if samples else None

    jitter = (
        statistics.mean(
            abs(samples[i] - samples[i - 1])
            for i in range(1, len(samples))
        )
        if len(samples) > 1 else (0.0 if samples else None)
    )

    rate = successes / attempts * 100

    if avg is None:
        score = 0.0
    else:
        latency_score = max(0, 100 - min(avg, 500) / 5)
        jitter_score = max(0, 100 - min(jitter or 0, 100))
        score = round(
            0.5 * rate + 0.3 * latency_score + 0.2 * jitter_score,
            1
        )

    result = {
        "tested_at": datetime.now().astimezone().isoformat(
            timespec="seconds"
        ),
        "host": host,
        "port": port,
        "attempts": attempts,
        "successes": successes,
        "failures": failures,
        "avg_latency": round(avg, 2) if avg is not None else None,
        "min_latency": round(minimum, 2) if minimum is not None else None,
        "max_latency": round(maximum, 2) if maximum is not None else None,
        "jitter": round(jitter, 2) if jitter is not None else None,
        "success_rate": round(rate, 1),
        "health_score": score
    }

    return result, pd.DataFrame(rows)


def dns_diagnostic(host):
    start = time.perf_counter()
    try:
        addresses = sorted({
            item[4][0]
            for item in socket.getaddrinfo(host, None)
        })
        elapsed = (time.perf_counter() - start) * 1000
        return addresses, round(elapsed, 2), None
    except OSError as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return [], round(elapsed, 2), str(exc)


init_db()

st.title("📡 NetQoS Monitor")
st.caption("Network Quality of Service Monitoring System")
st.info(
    "Tests run from the cloud server hosting this app, "
    "not directly from your laptop's Wi-Fi."
)

with st.sidebar:
    st.header("⚙️ Test settings")
    host_text = st.text_area(
        "Hostnames (one per line)",
        "google.com\ncloudflare.com"
    )
    port = st.number_input(
        "TCP port", min_value=1, max_value=65535, value=443
    )
    attempts = st.slider(
        "Attempts per host", 3, 30, 10
    )
    timeout = st.slider(
        "Connection timeout (seconds)", 1, 8, 3
    )
    latency_limit = st.slider(
        "Latency alert threshold (ms)", 10, 1000, 150, step=10
    )
    jitter_limit = st.slider(
        "Jitter alert threshold (ms)", 1, 200, 30
    )

hosts = list(dict.fromkeys(
    line.strip() for line in host_text.splitlines()
    if line.strip()
))[:10]

dashboard, diagnostics, history_tab, reports, about = st.tabs([
    "📊 Dashboard",
    "🧭 Diagnostics",
    "🕘 History",
    "📄 Reports",
    "ℹ️ About"
])

with dashboard:
    st.subheader("Network dashboard")
    st.write("Selected hosts:", ", ".join(hosts) or "None")

    if st.button("▶ Run live test", type="primary"):
        if not hosts:
            st.error("Enter at least one hostname.")
        elif any(not valid_host(host) for host in hosts):
            st.error(
                "Enter valid hostnames only, without https:// or paths."
            )
        else:
            results = []
            details = []

            progress = st.progress(0)

            for index, host in enumerate(hosts):
                result, detail = tcp_test(
                    host, int(port), int(attempts), int(timeout)
                )
                save_result(result)
                results.append(result)
                detail.insert(0, "Host", host)
                details.append(detail)
                progress.progress((index + 1) / len(hosts))

            st.session_state["results"] = pd.DataFrame(results)
            st.session_state["details"] = pd.concat(
                details, ignore_index=True
            )
            st.success("Tests completed and results saved.")

    if "results" in st.session_state:
        df = st.session_state["results"]

        total_attempts = int(df["attempts"].sum())
        total_successes = int(df["successes"].sum())
        overall_rate = (
            total_successes / total_attempts * 100
            if total_attempts else 0
        )

        valid_latency = df["avg_latency"].dropna()
        overall_latency = (
            valid_latency.mean() if not valid_latency.empty else None
        )

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Hosts tested", len(df))
        c2.metric("Success rate", f"{overall_rate:.1f}%")
        c3.metric(
            "Average connection time",
            f"{overall_latency:.2f} ms"
            if overall_latency is not None else "N/A"
        )
        c4.metric(
            "Average health score",
            f"{df['health_score'].mean():.1f}/100"
        )

        st.subheader("Latest results")
        st.dataframe(df, use_container_width=True, hide_index=True)

        chart_df = df.set_index("host")
        left, right = st.columns(2)

        with left:
            st.markdown("**Average TCP connection time (ms)**")
            st.bar_chart(chart_df[["avg_latency"]])

        with right:
            st.markdown("**Connection success rate (%)**")
            st.bar_chart(chart_df[["success_rate"]])

        st.markdown("**Jitter proxy (ms)**")
        st.bar_chart(chart_df[["jitter"]])

        st.subheader("⚠️ Alerts")
        for _, row in df.iterrows():
            alerts = []

            if row["failures"] > 0:
                alerts.append(f"{int(row['failures'])} failed attempts")

            if (
                pd.notna(row["avg_latency"])
                and row["avg_latency"] > latency_limit
            ):
                alerts.append("latency above threshold")

            if (
                pd.notna(row["jitter"])
                and row["jitter"] > jitter_limit
            ):
                alerts.append("jitter proxy above threshold")

            if alerts:
                st.warning(f"{row['host']}: " + ", ".join(alerts))
            else:
                st.success(f"{row['host']}: no configured alerts")

        with st.expander("Attempt-by-attempt diagnostics"):
            st.dataframe(
                st.session_state["details"],
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("Run a test to display live measurements.")

with diagnostics:
    st.subheader("DNS and TCP diagnostics")
    diagnostic_host = st.text_input(
        "Hostname to diagnose", value="google.com"
    )
    diagnostic_port = st.number_input(
        "Diagnostic port",
        min_value=1,
        max_value=65535,
        value=443,
        key="diagnostic_port"
    )

    if st.button("Run diagnostics"):
        if not valid_host(diagnostic_host.strip()):
            st.error("Enter a valid hostname.")
        else:
            addresses, dns_ms, dns_error = dns_diagnostic(
                diagnostic_host.strip()
            )
            st.metric("DNS lookup time", f"{dns_ms:.2f} ms")

            if addresses:
                st.write("Resolved IP addresses:")
                st.code("\n".join(addresses))
            else:
                st.error(f"DNS lookup failed: {dns_error}")

            start = time.perf_counter()
            try:
                with socket.create_connection(
                    (diagnostic_host.strip(), int(diagnostic_port)),
                    timeout=int(timeout)
                ):
                    elapsed = (time.perf_counter() - start) * 1000
                st.success(
                    f"TCP connection succeeded in {elapsed:.2f} ms."
                )
            except OSError as exc:
                st.error(f"TCP connection failed: {exc}")

with history_tab:
    st.subheader("Saved test history")
    history_df = load_history()

    if history_df.empty:
        st.info("No saved results yet. Run a live test first.")
    else:
        options = sorted(history_df["host"].dropna().unique())
        selected = st.multiselect(
            "Filter hosts", options, default=options
        )
        filtered = history_df[
            history_df["host"].isin(selected)
        ]

        st.dataframe(
            filtered, use_container_width=True, hide_index=True
        )

        if not filtered.empty:
            trend = filtered.sort_values("tested_at").set_index(
                "tested_at"
            )
            st.markdown("**Historical average connection time (ms)**")
            st.line_chart(trend[["avg_latency"]])
            st.markdown("**Historical success rate (%)**")
            st.line_chart(trend[["success_rate"]])

with reports:
    st.subheader("Reports and exports")
    report_df = load_history()

    if report_df.empty:
        st.info("Run a test before exporting a report.")
    else:
        st.download_button(
            "⬇ Download history as CSV",
            data=report_df.to_csv(index=False).encode("utf-8"),
            file_name="netqos_history.csv",
            mime="text/csv",
            type="primary"
        )
        st.dataframe(
            report_df.head(20),
            use_container_width=True,
            hide_index=True
        )

with about:
    st.subheader("About this project")
    st.markdown("""
    **NetQoS Monitor** is a Python and Streamlit network monitoring app.

    - TCP connection time: time required to establish a TCP connection.
    - Success rate: successful connections divided by total attempts.
    - Jitter proxy: average change between consecutive successful
      connection-time samples.
    - Health score: a custom illustrative score, not an official
      QoS standard.
    - DNS diagnostics: checks hostname resolution and timing.
    - History and reports: stores results in SQLite and exports CSV.
    """)

    st.warning(
        "This app does not measure true ICMP ping RTT or directly "
        "measure your laptop's Wi-Fi. Cloud-hosted SQLite history may "
        "not survive a server restart or redeployment."
    )
