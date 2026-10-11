"""
Production Gunicorn Configuration for TravelERP (Siva Gayathri Tours & Travels).
Optimized for high-concurrency multi-core deployments with 300+ live tracking vehicles.
"""

import os
import multiprocessing

# Server Socket Binding
bind = os.getenv("GUNICORN_BIND", "127.0.0.1:8000")
backlog = 2048

# Worker Processes & Concurrency
# Rule of thumb: (2 * CPUs) + 1 workers
cpu_count = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", max(2, (2 * cpu_count) + 1)))

# Worker Model:
# 'uvicorn.workers.UvicornWorker' for high-performance ASGI async handling
# 'gthread' for multi-threaded WSGI workloads
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "uvicorn.workers.UvicornWorker")
threads = int(os.getenv("GUNICORN_THREADS", 4))
worker_connections = 1024

# Worker Lifecycle & Memory Leak Protection
# Periodically recycle worker processes after serving N requests to prevent memory bloat
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 1200))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 100))

# Timeouts
timeout = 60
graceful_timeout = 30
keepalive = 5

# Preloading
# Preloads application in master process before forking workers.
# Drastically lowers per-worker memory footprint via Copy-on-Write (CoW).
preload_app = True

# Security & Reverse Proxy Forwarding
forwarded_allow_ips = "*"
secure_scheme_headers = {
    'X-FORWARDED-PROTOCOL': 'ssl',
    'X-FORWARDED-PROTO': 'https',
    'X-FORWARDED-SSL': 'on'
}

# Logging
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sµs'

# Process Naming
proc_name = "travelerp_gunicorn_master"


def on_starting(server):
    server.log.info("=" * 60)
    server.log.info("🚀 Starting TravelERP Production Gunicorn Server")
    server.log.info(f"⚡ Binding: {bind} | Workers: {workers} | Worker Class: {worker_class}")
    server.log.info("=" * 60)


def post_fork(server, worker):
    server.log.debug(f"Worker spawned (PID: {worker.pid})")


def worker_int(worker):
    worker.log.info(f"Worker interrupted (PID: {worker.pid})")


def worker_abort(worker):
    worker.log.warning(f"Worker aborted due to timeout (PID: {worker.pid})")
