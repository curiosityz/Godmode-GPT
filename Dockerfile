FROM python:3.11-slim
ENV PIP_NO_CACHE_DIR=yes
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
EXPOSE 8080

CMD ["python", "api.py"]
