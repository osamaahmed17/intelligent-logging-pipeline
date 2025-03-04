#!/bin/sh
echo "Replacing env variables MY_PORT=$MY_PORT, MY_DOMAIN=$MY_DOMAIN"
envsubst '$MY_PORT,$MY_DOMAIN' < /etc/nginx/nginx-template.conf > /etc/nginx/nginx.conf
echo "Replacing done"
exec nginx -g 'daemon off;'