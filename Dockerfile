FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y build-essential

# Copy requirements
COPY requirements/ /app/requirements/


RUN pip install --no-cache-dir -r requirements/requirements.txt


# Copy project
COPY . .

# Expose API port
EXPOSE 8000


CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

