# Use a lightweight Python image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . .

# Expose port 5000 (Heroku listens on this port)
EXPOSE 5000

# Run the bot
CMD ["python", "main.py"]
