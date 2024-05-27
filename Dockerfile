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
    TIMEOUT=0

# command to start the webserver and run the app
CMD exec gunicorn --bind :$PORT --workers $WORKERS --threads $THREADS --timeout $TIMEOUT run:app