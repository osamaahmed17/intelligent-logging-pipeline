FROM python:3.9-slim

WORKDIR /src

RUN pip install drain3

COPY drain3_processor.py .

CMD ["python", "drain3_processor.py"]