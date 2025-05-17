FROM python:3.8-alpine
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application files
COPY . .

# Create and populate Catalog directory
RUN mkdir -p /app/Catalog
COPY Catalog/catalog.json /app/Catalog/catalog.json

EXPOSE 8082
CMD ["python", "main.py"]