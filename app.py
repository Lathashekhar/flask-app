from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import Counter, Histogram, generate_latest
import subprocess
import requests
import time

app = FastAPI(title="AI DevOps Assistant")

# Allow HTML page to call FastAPI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# Prometheus Metrics
# ==========================

REQUEST_COUNT = Counter(
    "analysis_requests_total",
    "Total number of AI analysis requests"
)

FAILED_REQUESTS = Counter(
    "analysis_failed_total",
    "Total number of failed analysis requests"
)

REQUEST_DURATION = Histogram(
    "analysis_duration_seconds",
    "Time taken to analyze Kubernetes pods"
)

# ==========================
# Home Endpoint
# ==========================

@app.get("/")
def home():
    return {
        "message": "AI DevOps Assistant Running"
    }

# ==========================
# Metrics Endpoint
# ==========================

@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

# ==========================
# AI Analysis Endpoint
# ==========================

@app.get("/analyze/{pod_name}")
def analyze(pod_name: str):

    REQUEST_COUNT.inc()

    start_time = time.time()

    try:
        describe = subprocess.check_output(
            [
                "kubectl",
                "describe",
                "pod",
                pod_name
            ],
            text=True,
            stderr=subprocess.STDOUT
        )

    except subprocess.CalledProcessError as e:

        FAILED_REQUESTS.inc()

        return {
            "error": "Pod not found",
            "details": e.output
        }

    try:

        logs = subprocess.check_output(
            [
                "kubectl",
                "logs",
                pod_name
            ],
            text=True,
            stderr=subprocess.STDOUT
        )

    except subprocess.CalledProcessError:

        logs = "No logs available."

    prompt = f"""
You are a Senior Kubernetes Engineer.

Analyze the following Kubernetes pod.

=========================
POD DESCRIPTION
=========================

{describe}

=========================
POD LOGS
=========================

{logs}

Provide:

1. Current Status
2. Root Cause
3. Impact
4. Resolution Steps
5. Verification Commands

Be specific.
Use Kubernetes best practices.
"""

    try:

        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=300
        )

        response.raise_for_status()

        result = response.json()

    except Exception as e:

        FAILED_REQUESTS.inc()

        return {
            "error": "Failed to communicate with Ollama",
            "details": str(e)
        }

    REQUEST_DURATION.observe(time.time() - start_time)

    return {
        "analysis": result.get("response", "No response received")
    }

