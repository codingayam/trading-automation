"""
Gunicorn configuration for production deployment.
"""
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.getenv('DASHBOARD_PORT', '5000')}"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = os.getenv('GUNICORN_ACCESS_LOG', 'logs/gunicorn_access.log')
errorlog = os.getenv('GUNICORN_ERROR_LOG', 'logs/gunicorn_error.log')
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'trading_dashboard'

# Server mechanics
daemon = False
pidfile = os.getenv('GUNICORN_PID_FILE', 'tmp/gunicorn.pid')
user = None
group = None
tmp_upload_dir = None

# SSL (if needed)
keyfile = os.getenv('SSL_KEY_FILE')
certfile = os.getenv('SSL_CERT_FILE')

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Application
preload_app = True

# Hooks
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Gunicorn master process starting...")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Gunicorn reloading...")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Gunicorn server ready on {bind}")

def worker_int(worker):
    """Called just after a worker has been exited on SIGINT or SIGQUIT."""
    worker.log.info(f"Worker {worker.pid} received SIGINT/SIGQUIT")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.debug(f"Worker {worker.pid} about to be forked")

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info(f"Worker {worker.pid} initialized")

def worker_abort(worker):
    """Called when a worker received the SIGABRT signal."""
    worker.log.warning(f"Worker {worker.pid} received SIGABRT")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")

def pre_request(worker, req):
    """Called just before a worker processes the request."""
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after a worker processes the request."""
    pass