FROM python:3.7-alpine

# Install pip dependencies
COPY requirements.txt /app/requirements.txt
WORKDIR /app
RUN apk --update add --virtual build-dependencies python3-dev build-base && \
    pip install --upgrade pip && \
    pip install --upgrade --no-cache-dir -r requirements.txt && \
    apk del build-dependencies

COPY . /app
EXPOSE 5000
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=development
ENV FLASK_APP=server
CMD ["flask", "run", "--host=0.0.0.0"]
