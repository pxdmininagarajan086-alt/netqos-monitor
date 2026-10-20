🌐 NetQoS Monitor

Network Quality of Service Monitoring and Diagnostics Dashboard

NetQoS Monitor is a web-based network diagnostics application built using Python and Streamlit. It provides a simple, interactive dashboard to explore network connectivity and measure TCP connection performance.

🚀 Live Demo: https://netqos-monitor-b9zuqm5fav6qnutulp39bk.streamlit.app/

✨ Features

* 📊 Interactive Dashboard — View network diagnostic results in a clean interface.
* 🌐 Connectivity Testing — Test TCP connectivity to a specified host and port.
* ⏱️ Connection Time Measurement — Measure TCP connection establishment time.
* 📈 Performance Visualization — Explore connection timing through charts.
* 🧪 Network Diagnostics — Run basic network connectivity checks.
* 📁 CSV Export — Download available diagnostic results for further analysis.
* 🕘 Session History — Review test results collected during the current session.
* 🌙 Modern Dark UI — Use a dark-themed dashboard designed for readability.

🛠️ Technology Stack

* Language: Python
* Frontend and Dashboard: Streamlit
* Data Processing: Pandas
* Visualization: Streamlit charts
* Deployment: Streamlit Community Cloud
* Version Control: Git and GitHub

🚀 Run Locally

1. Clone the repository

git clone https://github.com/pxdmininagarajan086-alt/netqos-monitor.git

2. Open the project folder

cd netqos-monitor

3. Install dependencies

pip install -r requirements.txt

4. Start the application

streamlit run app.py

The application will open in your browser.

📋 Requirements

The project dependencies are listed in requirements.txt. They include Streamlit and Pandas.

⚠️ Important Notes

* Network tests run from the environment hosting the application, not directly from the visitor’s computer.
* TCP connection time is not the same as ICMP ping latency.
* Results depend on network conditions and destination availability.
* Session history may be cleared when the application session resets.

🔮 Future Improvements

* Continuous network monitoring
* Packet loss and latency analysis
* Historical data storage
* Network performance alerts
* Additional diagnostic visualizations

🎯 Project Objective

The objective of NetQoS Monitor is to provide a beginner-friendly tool for understanding network connectivity and basic performance diagnostics through an interactive web dashboard.

👨‍💻 Author

Developed as a B.Tech project to explore Python programming, networking concepts, data visualization, and web application deployment.

⸻

⭐ If you find this project useful, consider giving the repository a star!
