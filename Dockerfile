ENV PIP_NO_CACHE_DIR=yes
FROM python:3.11-slim-bullseye

WORKDIR /app
COPY scripts/ /app
COPY requirements.txt /app
COPY gunicorn.conf.py /app
COPY credentials/ /app/credentials

RUN pip install -r requirements.txt
EXPOSE 8080

ENV PORT 8080
ENV HOST 0.0.0.0

CMD ["gunicorn" , "-c", "gunicorn.conf.py" , "--timeout", "800", "api:app"]
