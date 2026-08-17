output "api_base_url" {
  value       = aws_apigatewayv2_api.http.api_endpoint
  description = "Base URL of the backend. LTI redirect_uri is <api_base_url>/lti/launch."
}

output "ecr_api_repo" {
  value = aws_ecr_repository.api.repository_url
}

output "ecr_worker_repo" {
  value = aws_ecr_repository.worker.repository_url
}

output "secrets_arn" {
  value = aws_secretsmanager_secret.app.arn
}
