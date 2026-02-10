from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import datetime

app = FastAPI()

# Simulated workflow tasks
workflow_data = [
    {"task": "Bot Started", "status": "Completed", "time": str(datetime.datetime.now())},
    {"task": "Listening to messages", "status": "Running", "time": str(datetime.datetime.now())},
]

# Color mapping for status
status_colors = {
    "Completed": "#28a745",  # green
    "Running": "#ffc107",    # yellow
    "Failed": "#dc3545"      # red
}

@app.get("/", response_class=HTMLResponse)
def dashboard():
    # Build HTML table rows dynamically
    rows = ""
    for task in workflow_data:
        color = status_colors.get(task["status"], "#6c757d")  # gray default
        rows += f"""
        <tr>
            <td>{task['task']}</td>
            <td style="color:{color}; font-weight:bold;">{task['status']}</td>
            <td>{task['time'].split('.')[0]}</td>
        </tr>
        """

    html_content = f"""
    <html>
        <head>
            <title>WhatsFlow Dashboard</title>
            <meta http-equiv="refresh" content="5"> <!-- auto-refresh every 5s -->
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: #1e1e2f;
                    color: #f0f0f0;
                    margin: 0;
                    padding: 0;
                }}
                header {{
                    background: #343a40;
                    padding: 20px;
                    text-align: center;
                    font-size: 28px;
                    font-weight: bold;
                    color: #ff6b6b;
                    letter-spacing: 1px;
                }}
                .container {{
                    padding: 30px;
                    max-width: 800px;
                    margin: auto;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    background: #2b2b3d;
                    border-radius: 10px;
                    overflow: hidden;
                    box-shadow: 0 0 20px #00000044;
                }}
                th, td {{
                    padding: 15px;
                    text-align: left;
                }}
                th {{
                    background: #343a40;
                    color: #ffffffaa;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                tr:nth-child(even) {{
                    background: #23232f;
                }}
                footer {{
                    text-align: center;
                    padding: 15px;
                    color: #888;
                    margin-top: 20px;
                    font-size: 14px;
                }}
            </style>
        </head>
        <body>
            <header>WhatsFlow Dashboard</header>
            <div class="container">
                <table>
                    <tr>
                        <th>Task</th>
                        <th>Status</th>
                        <th>Time</th>
                    </tr>
                    {rows}
                </table>
            </div>
            <footer>Last updated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</footer>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)
