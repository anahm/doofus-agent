# declare what image to use
# FROM username/image_name:tag
FROM python:3.13.4-slim-bullseye

# Need to install curl
# This is to run "host.docker.internal" instead of "localhost"
# curl -X POST -d '{"message": "Hello world"}' -H "Content-Type: application/json" http://host.docker.internal:8080/api/chats/
RUN apt-get update && apt-get install -y curl

# Create a python virtual environment to isolate python from system-level python
# (doesn't muck with system python functions)
# Want to go into "optional software" in the venv to setup the Docker container
RUN python -m venv /opt/venv/

# Ensure everything run after will use the virtual environment python version
ENV PATH=/opt/venv/bin:$PATH

# Set a working directory for the following commands, similar to "mkdir -p /app" + "cd / app"
# The folder will always be there
WORKDIR /app

# Set the parameters for how this will work and run
# Copy python requirements and install
COPY requirements.txt /tmp/requirements.txt
# Download into the virtual environment itself
RUN pip install -r /tmp/requirements.txt


# Ensures a folder is in the container: RUN mkdir -p /static_folder
# Copy a local folder into the container, relative to the dockerfile itself
COPY ./src /app

# To run a Python webserver: python -m http.server 8000
# Has to be a list in double quotes
# Making sure it's served as an HTML file, won't allow to browse the rest of the directories
CMD ["python", "-m", "http.server", "8000"]