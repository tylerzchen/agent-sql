# Use AWS Lambda Python 3.9 runtime
FROM public.ecr.aws/lambda/python:3.9

# Copy requirements-lambda.txt for better caching
COPY requirements-lambda.txt .

# Install dependencies
RUN pip install -r requirements-lambda.txt

# Copy the rest of the application code
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Set the CMD to the handler function
CMD ["lambda_handler.lambda_handler"]