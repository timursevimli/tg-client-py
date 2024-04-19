FROM python:3.12.3-alpine AS builder
WORKDIR /usr/src/app
COPY requirements.txt .
RUN apk add --no-cache gcc musl-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apk del gcc musl-dev
COPY . .

FROM python:3.12.3-alpine3.19
WORKDIR /usr/src/app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/src/app .
CMD ["python", "main.py"]
