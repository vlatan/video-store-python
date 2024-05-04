# Docker image
FROM python:3.11-slim

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

# command to start the webserver and run the app
# by default with 1 worker, 6 threads, on port 8000
CMD gunicorn \
    --bind :${PORT:-8000} \
    --workers ${$WORKERS:-1} \
    --threads ${THREADS:-6} \
    --timeout ${TIMEOUT:-0} \
    run:app