# Docker image
FROM python:3.10-slim

# set the container's working directory
WORKDIR /doxder

# copy requirements file and install dependencies
COPY ./requirements.txt /doxder
RUN pip install --upgrade pip
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# copy all of the app files to the working directory
COPY . /doxder

# command to start the webserver and run the app (with 3 workers)
CMD ["gunicorn", "-w", "3", "-b", "0.0.0.0", "run:app"]