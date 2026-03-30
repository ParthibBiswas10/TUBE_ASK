FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy entire repo
COPY . .

# Install dependencies from flow folder
RUN pip install --no-cache-dir -r flow/requirements.txt

# Expose the FastAPI port
EXPOSE 8080

# Run your app from flow
CMD ["python", "flow/main.py"]
