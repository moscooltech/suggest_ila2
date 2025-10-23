# Gunicorn configuration for production deployment

# Server socket
bind = "0.0.0.0:10000"
backlog = 2048

# Worker processes
workers = 2
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Process naming
proc_name = "suggestion_app"

# Server mechanics
preload_app = True
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# Application
wsgi_module = "wsgi:app"
pythonpath = "/opt/render/project/src"

# SSL (if needed)
keyfile = None
certfile = None

# Development overrides (uncomment for local testing)
# bind = "127.0.0.1:8000"
# workers = 1
# loglevel = "debug"