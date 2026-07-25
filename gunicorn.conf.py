# SISPM - Gunicorn Configuration

import os
import multiprocessing

basedir = os.path.abspath(os.path.dirname(__file__))

# Server socket
bind = "0.0.0.0:" + os.environ.get("PORT", "5000")
backlog = 2048

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 100

# Logging
log_dir = os.path.join(basedir, 'logs')
os.makedirs(log_dir, exist_ok=True)
accesslog = os.path.join(log_dir, "access.log")
errorlog = os.path.join(log_dir, "error.log")
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'sispm'

# Server mechanics
daemon = False
tmp_upload_dir = '/tmp'

# Security
limit_request_fields = 100
limit_request_field_size = 8190
limit_request_line = 4094

# Performance
preload_app = True

# Graceful shutdown
graceful_timeout = 30

# Hooks
def on_starting(server):
    server.log.info("Starting SISPM application")

def on_reload(server):
    server.log.info("Reloading SISPM application")

def when_ready(server):
    server.log.info("SISPM application ready")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info(f"Worker spawned (pid: {worker.pid})")

def post_fork(server, worker):
    server.log.info(f"Worker initialized (pid: {worker.pid})")

def child_exit(server, worker):
    server.log.info(f"Worker exited (pid: {worker.pid})")