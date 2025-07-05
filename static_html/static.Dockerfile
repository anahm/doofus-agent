# declare what image to use
# FROM username/image_name:tag
FROM python:3.13.4-slim-bullseye

# Set a working directory for the following commands, similar to "mkdir -p /app" + "cd / app"
# The folder will always be there
WORKDIR /app

# Ensures a folder is in the container: RUN mkdir -p /static_folder
# Copy a local folder into the container, relative to the dockerfile itself
COPY ./src /app

# Create an HTML file with a specific Linux command
# RUN echo "hello" > index.html

# To run a Python webserver: python -m http.server 8000
# Has to be a list in double quotes
# Making sure it's served as an HTML file, won't allow to browse the rest of the directories
CMD ["python", "-m", "http.server", "8000"]

# To just run a the standard Dockerfile
# docker build -f Dockerfile -t anahmtribe/ai-py-app-test:latest .

# To open a python environment: docker run -it anahmtribe/ai-py-app-test:latest
# To also grant a Docker container to run on a particular port on my local machine: -p (port on my localhost):(port that my container host is running on)
# Local computer is now opening up port 3000 for the container running port 8000
#     docker run -it -p 3000:8000 anahmtribe/ai-py-app-test:latest