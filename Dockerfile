FROM python:3.9-alpine AS builder
WORKDIR /usr/src/app
COPY requirements.txt .
RUN apk add --no-cache gcc musl-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del gcc musl-dev
COPY main.py .

FROM python:3.9-alpine
WORKDIR /usr/src/app
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/src/app .
CMD ["python", "main.py"]
