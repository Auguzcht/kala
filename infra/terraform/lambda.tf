resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/kala-api"
  retention_in_days = 30
}

resource "aws_lambda_function" "api" {
  function_name = "kala-api"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = var.api_image_uri
  timeout       = 30
  memory_size   = 1024

  environment {
    variables = {
      KALA_SECRETS_ARN = aws_secretsmanager_secret.app.arn
      FRONTEND_URL     = var.frontend_url
    }
  }

  depends_on = [aws_cloudwatch_log_group.api]
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/kala-worker"
  retention_in_days = 30
}

resource "aws_lambda_function" "worker" {
  function_name = "kala-worker"
  role          = aws_iam_role.lambda.arn
  package_type  = "Image"
  image_uri     = var.worker_image_uri
  timeout       = 120
  memory_size   = 1024

  environment {
    variables = {
      KALA_SECRETS_ARN = aws_secretsmanager_secret.app.arn
    }
  }

  depends_on = [aws_cloudwatch_log_group.worker]
}
