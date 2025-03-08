#!/bin/sh

# Print a message indicating which environment variables will be replaced
echo "Replacing env variables MY_PORT=$MY_PORT, MY_DOMAIN=$MY_DOMAIN"

# Use envsubst to replace placeholders in the Nginx template with actual environment variable values
envsubst '$MY_PORT,$MY_DOMAIN' < /etc/nginx/nginx-template.conf > /etc/nginx/nginx.conf

# Confirm replacement is done
echo "Replacing done"

# Start Nginx in the foreground to keep the container running
exec nginx -g 'daemon off;'