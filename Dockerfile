# Docker image
FROM python:3.12-slim

# create virtual environment and prepend its bin dir in $PATH
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}" \
    # Allow statements and log messages to immediately appear in logs
    PYTHONUNBUFFERED=1

# set the container's working directory
WORKDIR /src

# copy requirements file and install dependencies
COPY ./requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --upgrade -r requirements.txt

# copy all the necessary app files into the working dir
COPY ["./config.py", "./run.py", "worker.py", "./"]
COPY ./app ./app

# default environment vars
ENV PORT=8000 \
    WORKERS=1 \
    THREADS=6 \
    TIMEOUT=0 \
    ACCESS_LOGFILE='-' \
    ACCESS_LOGFORMAT='{\
    "remote_address": "%({cf-connecting-ip}i)s", \
    "date": "%(t)s", \
    "status": "%(r)s", \
    "response_code": "%(s)s", \
    "response_length": "%(b)s", \
    "referrer": "%(f)s", \
    "user_agent": "%(a)s", \
    "request_time": "%(M)sms"\
    }'

# command to start the webserver and run the app
# https://developers.cloudflare.com/fundamentals/reference/http-request-headers/
# https://docs.gunicorn.org/en/stable/settings.html
CMD sleep 5 && \
    exec gunicorn \
    --bind :$PORT \
    --workers $WORKERS \
    --threads $THREADS \
    --timeout $TIMEOUT \
    --access-logfile $ACCESS_LOGFILE \
    --access-logformat ${ACCESS_LOGFORMAT} \
    run:app