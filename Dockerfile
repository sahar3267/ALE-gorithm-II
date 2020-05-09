# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8

# Copy local code to the container image.
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./
RUN pip install Flask gunicorn sqlalchemy pandas pymysql numpy scikit-surprise
# Install production dependencies
RUN pip install pipenv

# Run the web service on container startup. Here we use the gunicorn
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 app:app