
## ------------------------------- Build Stage ------------------------------ ##

FROM python:3.12-slim AS builder

# set the container's working directory
WORKDIR /src

# install dependencies in .venv using uv
COPY requirements.txt .
RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv venv && uv pip install --no-cache-dir --upgrade -r requirements.txt


## ------------------------------- Runtime Stage ------------------------------ ##

FROM python:3.12-slim

# set the container's working directory
WORKDIR /src

# copy only the necessary app files into the working dir
COPY app/ config.py gunicorn.conf.py run.py worker.py ./

# copy the .venv from the builder stage
COPY --from=builder /src/.venv ./.venv

# set the virtual environment path
ENV PATH="/src/.venv/bin:${PATH}" \
    # allow statements and log messages to immediately appear in logs
    PYTHONUNBUFFERED=1

# command to start the webserver and run the app
# gets config from `gunicorn.conf.py`
CMD ["gunicorn", "run:app"]