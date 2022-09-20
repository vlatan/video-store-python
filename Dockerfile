# Docker image
FROM python:latest

# set peristent volumes
VOLUME ["./index", "./app/static"]

# set the container's working directory
WORKDIR /doxder

# copy requirements file and install dependencies
COPY ./requirements.txt /doxder
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# copy all of the app files to the working directory
COPY . /doxder

# command to start the webserver and run the app (with 3 workers)
CMD ["gunicorn -w 3 run:app"]