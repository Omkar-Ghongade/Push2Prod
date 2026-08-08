#!/usr/bin/env python3
"""TraceTalk server — Flask backend with SSE streaming endpoint."""

import json
import queue
import threading

from flask import Flask, Response, request, send_from_directory

from agent import run_agent_stream

app = Flask(__name__, static_folder="static")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


@app.route("/ask", methods=["POST"])
def ask():
    """Stream agent investigation events via Server-Sent Events."""
    data = request.get_json()
    question = data.get("question", "")

    def generate():
        q = queue.Queue()

        def producer():
            try:
                for event in run_agent_stream(question):
                    q.put(event)
            except Exception as e:
                import traceback
                traceback.print_exc()
                q.put({"type": "error", "text": str(e)})
            finally:
                q.put(None)  # sentinel

        thread = threading.Thread(target=producer, daemon=True)
        thread.start()

        while True:
            event = q.get()
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


if __name__ == "__main__":
    print("TraceTalk server starting on http://localhost:5050")
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)
