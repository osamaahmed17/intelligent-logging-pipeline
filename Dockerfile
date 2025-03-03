# Use the official NGINX image as the base
FROM nginx:latest

# Copy our custom HTML file to the NGINX HTML directory
COPY ./files/index.html /usr/share/nginx/html/index.html

# Copy our minimal custom NGINX config
COPY ./files/nginx-template.conf /etc/nginx/nginx-template.conf

# Expose port 80
EXPOSE 80

# Copy the shell script
COPY ./files/start-nginx.sh /start-nginx.sh

# Make the script executable
RUN chmod +x /start-nginx.sh

# Start NGINX using the script
CMD ["/start-nginx.sh"]