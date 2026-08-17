# Lambda container image for the FastAPI backend (handles heavy deps cleanly).
FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Mangum entrypoint: app.main.handler wraps the FastAPI app for Lambda.
CMD ["app.main.handler"]
