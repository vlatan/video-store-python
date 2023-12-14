# Docker image
FROM python:3.10-slim

# Allow statements and log messages to immediately appear in logs
ENV PYTHONUNBUFFERED True

# run and add virtual env in PATH
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# set the container's working directory
WORKDIR /app

# copy requirements file and install dependencies
COPY ./requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# copy all of the app files to the working directory
COPY . .

# command to start the webserver and run the app (with 3 workers)
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0", "run:app"]