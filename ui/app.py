"""
BTR Tool Selector UI
Flask-based web interface for managing MCP tool selection
"""
import os
import json
import requests
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# Gateway API URL - configurable via environment
GATEWAY_URL = os.getenv("BTR_GATEWAY_URL", "http://gateway:8090")


def gateway_request(method: str, endpoint: str, data: dict = None) -> dict:
    """Make a request to the BTR Gateway API"""
    url = f"{GATEWAY_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        else:
            response = requests.post(url, json=data, timeout=10)
        return response.json()
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# Web UI Routes
# =============================================================================

@app.route("/")
def index():
    """Main tool selector page"""
    return render_template("index.html")


# =============================================================================
# API Routes (proxy to Gateway)
# =============================================================================

@app.route("/api/tools")
def get_tools():
    """Get all available tools"""
    return jsonify(gateway_request("GET", "/api/tools"))


@app.route("/api/current")
def get_current():
    """Get currently enabled tools"""
    return jsonify(gateway_request("GET", "/api/current"))


@app.route("/api/update", methods=["POST"])
def update_tools():
    """Update enabled tools"""
    data = request.get_json()
    return jsonify(gateway_request("POST", "/api/update", data))


@app.route("/api/tools/enable", methods=["POST"])
def enable_tool():
    """Enable a specific tool"""
    data = request.get_json()
    return jsonify(gateway_request("POST", "/api/tools/enable", data))


@app.route("/api/tools/disable", methods=["POST"])
def disable_tool():
    """Disable a specific tool"""
    data = request.get_json()
    return jsonify(gateway_request("POST", "/api/tools/disable", data))


@app.route("/api/tools/toggle", methods=["POST"])
def toggle_tool():
    """Toggle a tool's enabled state"""
    data = request.get_json()
    return jsonify(gateway_request("POST", "/api/tools/toggle", data))


@app.route("/api/presets")
def list_presets():
    """List available presets"""
    return jsonify(gateway_request("GET", "/api/presets"))


@app.route("/api/presets/load", methods=["POST"])
def load_preset():
    """Load a preset"""
    data = request.get_json()
    return jsonify(gateway_request("POST", "/api/presets/load", data))


@app.route("/health")
def health():
    """Health check"""
    gateway_health = gateway_request("GET", "/health")
    return jsonify({
        "status": "healthy",
        "gateway": gateway_health
    })


if __name__ == "__main__":
    port = int(os.getenv("BTR_UI_PORT", 5010))
    host = os.getenv("BTR_UI_HOST", "0.0.0.0")
    app.run(host=host, port=port, debug=os.getenv("DEBUG", "false").lower() == "true")
