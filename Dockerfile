# Use official Python image (closest match to 3.11.9)
FROM python:3.11-slim-buster

# Create working directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Run app with system Python
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "wsgi:app"]