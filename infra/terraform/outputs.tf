output "api_base_url" {
  value       = aws_apigatewayv2_api.http.api_endpoint
  description = "Base URL of the backend. LTI redirect_uri is <api_base_url>/lti/launch."
}

output "api_live_alias_arn" {
  value       = aws_lambda_alias.api_live.arn
  description = "Published API Lambda alias used by API Gateway and provisioned concurrency."
}

output "ecr_api_repo" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_worker_repo" {
  value = aws_ecr_repository.worker.repository_url
}

output "worker_function_arn" {
  value       = aws_lambda_function.worker.arn
  description = "ARN of the worker Lambda function invoked by the API."
}

output "secrets_arn" {
  value = aws_secretsmanager_secret.app.arn
}
