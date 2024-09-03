FROM python:3.11-slim

WORKDIR /app
VOLUME /mnt
ENV DB=/mnt/db.sqlite

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /app

ENTRYPOINT [ "python", "main.py" ]
