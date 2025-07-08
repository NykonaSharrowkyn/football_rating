# Use a slim Python base image for a smaller final image size
FROM python:3.11-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Prevent Python from writing .pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Update apt-get and install any necessary system dependencies
# Combine update and install in a single RUN command to optimize caching
# --no-install-recommends reduces the number of installed packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    # Add other system dependencies your application needs here
    # Example: git, curl, etc.
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements.txt file first to leverage Docker's build cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

RUN python --version
# Define the command to run your application
CMD ["python", "-m", "football_rating_bot"]