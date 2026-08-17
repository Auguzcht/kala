# The application secrets bundle. Populate the value out of band (console or
# CLI) so secrets never live in Terraform state:
#   aws secretsmanager put-secret-value --secret-id kala/app \
#     --secret-string file://secrets.json
resource "aws_secretsmanager_secret" "app" {
  name        = "kala/app"
  description = "Kala backend secrets: Supabase keys, JWT secret, LTI keys."
}
