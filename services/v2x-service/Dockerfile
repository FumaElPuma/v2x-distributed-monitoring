FROM python:3.12-slim
WORKDIR /app
COPY services/v2x-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY services/v2x-service/ .
COPY schema/ schema/
EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
