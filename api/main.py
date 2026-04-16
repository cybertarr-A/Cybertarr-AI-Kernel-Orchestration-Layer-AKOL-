import asyncio
import json
import sys
import os
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse
from typing import AsyncGenerator

# Ensure Python can find ai_engine if run from root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ai_engine.inference import start_inference_server

app = FastAPI(title="Cybertarr AKOL OS Engine V2", version="2.0.0")

event_queue = asyncio.Queue(maxsize=100)
action_log = []

HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cybertarr AKOL Real-Time Orchestration V2</title>
    <style>
        :root {
            --bg-color: #0b0c10;
            --panel-bg: #1f2833;
            --text-color: #c5c6c7;
            --accent-red: #ff3b3b;
            --accent-green: #45a29e;
            --accent-cyan: #66fcf1;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
        }

        h1 {
            color: var(--accent-red);
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(255, 59, 59, 0.5);
            text-align: center;
        }

        .container {
            display: grid;
            grid-template-columns: 2fr 1fr;
            grid-template-rows: auto auto;
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }

        .panel {
            background-color: var(--panel-bg);
            border: 1px solid var(--accent-red);
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 0 15px rgba(255, 59, 59, 0.1);
        }

        .panel h2 { margin-top: 0; color: var(--accent-cyan); border-bottom: 1px solid #333; padding-bottom: 10px; }

        #log-stream { height: 350px; overflow-y: auto; font-family: 'Courier New', Courier, monospace; background: #000; padding: 10px; border-radius: 4px; }

        .log-entry { margin-bottom: 5px; }
        .log-time { color: #888; }
        .log-pid { color: var(--accent-cyan); font-weight: bold; }
        .class-badge { background: #333; padding: 2px 6px; border-radius: 4px; font-size: 0.8em; margin: 0 5px; }
        .action-Boost { color: var(--accent-green); font-weight: bold; }
        .action-Noop { color: #aaa; }
        .action-Throttle { color: orange; font-weight: bold; }
        .action-Isolate { color: var(--accent-red); font-weight: bold; text-decoration: underline; }

        .stat-box { display: flex; justify-content: space-between; background: #000; padding: 15px; border-radius: 4px; margin-bottom: 10px; border-left: 4px solid var(--accent-cyan); }
        .stat-value { font-size: 1.5em; color: white; font-weight: bold; }

        #heatmap { height: 100px; background: #000; display: flex; align-items: flex-end; gap: 2px; padding: 5px; overflow: hidden; border-radius: 4px; margin-top: 10px; }
        .heat-bar { width: 10px; background: var(--accent-green); border-radius: 2px 2px 0 0; transition: height 0.2s; }
        .heat-warn { background: orange; }
        .heat-danger { background: var(--accent-red); }
    </style>
</head>
<body>
    <h1>Cybertarr AKOL Engine V2</h1>
    <div class="container">
        
        <div class="panel">
            <h2>AI Decision Timeline & Execution</h2>
            <div id="log-stream"></div>
        </div>

        <div class="panel">
            <h2>System Active Metrics</h2>
            <div class="stat-box" style="border-left-color: var(--accent-red);">
                <span>Total Actions Taken</span>
                <span class="stat-value" id="stat-actions">0</span>
            </div>
            <div class="stat-box" style="border-left-color: var(--accent-cyan);">
                <span>Unique Processes Validated</span>
                <span class="stat-value" id="stat-pids">0</span>
            </div>
            <div class="stat-box" style="border-left-color: var(--accent-green);">
                <span>Total Telemetry Processed</span>
                <span class="stat-value" id="stat-total">0</span>
            </div>
        </div>
        
        <div class="panel" style="grid-column: 1 / 3;">
            <h2>Global CPU Spike Heatmap</h2>
            <div id="heatmap"></div>
        </div>
    </div>

    <script>
        const logStream = document.getElementById('log-stream');
        const statActions = document.getElementById('stat-actions');
        const statPids = document.getElementById('stat-pids');
        const statTotal = document.getElementById('stat-total');
        const heatmap = document.getElementById('heatmap');

        let actionsCount = 0;
        let totalCount = 0;
        const uniquePids = new Set();
        const MAX_BARS = 130;

        const evtSource = new EventSource('/stream');
        
        evtSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            totalCount++;
            statTotal.innerText = totalCount;
            
            uniquePids.add(data.pid);
            statPids.innerText = uniquePids.size;

            if (data.action !== "Noop") {
                actionsCount++;
                statActions.innerText = actionsCount;
            }

            const timeStr = new Date().toLocaleTimeString();
            
            const logHtml = `
                <div class="log-entry">
                    <span class="log-time">[${timeStr}]</span> 
                    <span class="log-pid">PID: ${data.pid}</span> 
                    <span class="class-badge">${data.class}</span>
                    <span class="log-pid">(${data.comm})</span>
                    <span style="color:#aaa;margin-left:10px;">DUR: ${(data.duration_ns / 1000000).toFixed(2)}ms</span>
                    <span style="margin-left:10px;">RL_ACTION: <span class="action-${data.action}">[${data.action}]</span></span>
                    <span style="margin-left:10px;color:#777;">SYS_LOAD: ${(data.system_load*100).toFixed(1)}%</span>
                </div>
            `;
            
            logStream.insertAdjacentHTML('afterbegin', logHtml);
            if (logStream.children.length > 100) {
                logStream.removeChild(logStream.lastChild);
            }

            // Heatmap Bar (Based on duration ms)
            const ms = data.duration_ns / 1000000;
            let heatHeight = Math.min(ms, 100); 
            let heatClass = 'heat-bar';
            if (ms > 50) heatClass += ' heat-danger';
            else if (ms > 20) heatClass += ' heat-warn';
            
            const bar = document.createElement('div');
            bar.className = heatClass;
            bar.style.height = heatHeight + 'px';
            heatmap.appendChild(bar);
            
            if (heatmap.children.length > MAX_BARS) {
                heatmap.removeChild(heatmap.firstChild);
            }
        };
    </script>
</body>
</html>
"""

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(start_inference_server(event_queue))
    print("Cybertarr AKOL Inference Server Started background tasks.")

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    return HTML_CONTENT

async def event_generator() -> AsyncGenerator[str, None]:
    while True:
        try:
            event = await event_queue.get()
            action_log.append(event)
            if len(action_log) > 1000:
                action_log.pop(0)

            payload = json.dumps(event)
            yield f"data: {payload}\\n\\n"
        except asyncio.CancelledError:
            break

@app.get("/stream")
async def stream_events():
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "v2.0.0"}

@app.get("/control/actions")
async def get_recent_actions():
    return {"recent_actions": action_log[-50:]}

@app.get("/ai/decisions")
async def get_ai_decisions():
    return {"ai_decision_log": [log for log in action_log[-100:] if log['action'] != 'Noop']}

@app.get("/metrics")
async def get_metrics():
    return {"status": "running", "qsize": event_queue.qsize(), "events_retained": len(action_log)}
