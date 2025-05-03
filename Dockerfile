
## ------------------------------- Build Stage ------------------------------ ##

FROM python:3.12-slim AS builder

# create virtual environment
RUN python -m venv /opt/venv

# copy requirements file and install dependencies into the venv
COPY ./requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir --upgrade -r requirements.txt


## ------------------------------- Runtime Stage ------------------------------ ##

FROM python:3.12-slim

# set the container's working directory
WORKDIR /src

# copy only the necessary app files into the working dir
COPY ["./config.py", "./gunicorn.conf.py", "./run.py", "./worker.py", "./"]
COPY ./app ./app

# copy the .venv from the builder stage
COPY --from=builder /opt/venv /opt/venv

# set the virtual environment path
# allow statements and log messages to immediately appear in logs
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

# command to start the webserver and run the app
# gets config from `gunicorn.conf.py`
CMD ["gunicorn", "run:app"]