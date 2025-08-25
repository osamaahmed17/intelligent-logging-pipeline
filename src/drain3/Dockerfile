# FROM python:3.10-alpine

# RUN apk update && apk add --no-cache jq
# RUN pip install drain3 redis

# WORKDIR /app

# COPY forward_logs_to_drain3.py /app/
# COPY redis_store.py /app/
# COPY drain3.ini /app/

# RUN addgroup -S appgroup && adduser -S appuser -G appgroup
# RUN mkdir -p /var/drain3 && chown -R appuser:appgroup /app /var/drain3
# USER appuser

# CMD ["python3", "forward_logs_to_drain3.py"]

FROM python:3.10-alpine

# Install jq and dependencies
RUN apk add --no-cache bash curl jq unzip

# Install logcli (from Grafana Loki releases)
RUN curl -sL "https://github.com/grafana/loki/releases/download/v2.9.8/logcli-linux-amd64.zip" \
    -o /tmp/logcli.zip \
    && unzip /tmp/logcli.zip -d /usr/local/bin/ \
    && rm /tmp/logcli.zip \
    && mv /usr/local/bin/logcli-linux-amd64 /usr/local/bin/logcli \
    && chmod +x /usr/local/bin/logcli


# Install Python dependencies
RUN pip install drain3 redis

WORKDIR /app

# Copy application files
COPY forward_logs_to_drain3.py /app/
COPY redis_store.py /app/
COPY drain3.ini /app/
COPY drain3_state.bin /app/

# Create non-root user and set permissions
RUN addgroup -S appgroup && adduser -S appuser -G appgroup && \
    mkdir -p /var/drain3 && chown -R appuser:appgroup /app /var/drain3

USER appuser

# Entrypoint
CMD ["python", "/app/forward_logs_to_drain3.py"]
