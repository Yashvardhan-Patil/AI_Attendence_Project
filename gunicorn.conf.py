import os

# Dynamic port assignment
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

# Use 1 worker with 2 threads to stay strictly within 512MB RAM
workers = 1
threads = 2

# Worker timeout for ML model inference
timeout = 120

# Restart worker after 50 requests to purge memory fragments
max_requests = 50
max_requests_jitter = 5

# Do NOT preload app into master to avoid memory duplication
preload_app = False

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
