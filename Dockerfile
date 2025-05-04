FROM python:3.12-slim

# set the container's working directory
WORKDIR /src

# create virtual environment with uv and install dependencies
COPY requirements.txt .
RUN --mount=from=ghcr.io/astral-sh/uv:0.7.2,source=/uv,target=/bin/uv \
    uv venv && \
    uv pip install --no-cache-dir --upgrade -r requirements.txt && \
    rm requirements.txt

# prepend the virtual environment path in the PATH env var
ENV VIRTUAL_ENV=/src/.venv \
    PATH="/src/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

# copy only the necessary files into the working dir
COPY config.py gunicorn.conf.py run.py worker.py ./
COPY app ./app

# command to start the webserver and run the app
# gets config from `gunicorn.conf.py`
CMD ["gunicorn", "run:app"]