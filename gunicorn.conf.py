import os

# Full Gunicorn settings
# https://docs.gunicorn.org/en/stable/settings.html

# If PORT valiable in environment gunicorn will bind to "0.0.0.0:$PORT"
# https://docs.gunicorn.org/en/stable/settings.html#bind

# Get real remote address
# If behind CF proxy substitute %(h)s with %({cf-connecting-ip}i)s
# https://docs.gunicorn.org/en/stable/settings.html#access-log-format
# https://developers.cloudflare.com/fundamentals/reference/http-request-headers/

workers = int(os.getenv("WORKERS", 1))
threads = int(os.getenv("THREADS", 6))
timeout = int(os.getenv("TIMEOUT", 0))
accesslog = os.getenv("ACCESS_LOGFILE", "-")
access_log_format = os.getenv(
    "ACCESS_LOG_FORMAT", '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
)
