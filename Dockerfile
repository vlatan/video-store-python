
## ------------------------------- Build Stage ------------------------------ ##

FROM python:3.12-slim-bookworm AS builder

# install dependencies in .venv with uv
COPY requirements.txt .
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv venv && uv pip install --no-cache-dir --upgrade -r requirements.txt


## ------------------------------- Runtime Stage ------------------------------ ##

FROM python:3.12-slim-bookworm

# create user to avoid running as root
RUN useradd --create-home appuser
USER appuser

# set the container's working directory
WORKDIR /src

# copy only the necessary app files into the working dir
COPY ["./config.py", "./gunicorn.conf.py", "./run.py", "./worker.py", "./"]
COPY ./app ./app

# copy the .venv from the builder stage
COPY --from=builder /.venv /opt/venv

# set the virtual environment path
# allow statements and log messages to immediately appear in logs
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

# command to start the webserver and run the app
# gets config from `gunicorn.conf.py`
CMD ["gunicorn", "run:app"]