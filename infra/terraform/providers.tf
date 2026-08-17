# If the school gives you a cross-account role in their AWS Organization, set
# assume_role_arn. If they give you a standalone account, leave it empty and
# authenticate with a profile or environment credentials.
provider "aws" {
  region = var.region

  dynamic "assume_role" {
    for_each = var.assume_role_arn == "" ? [] : [1]
    content {
      role_arn     = var.assume_role_arn
      session_name = "kala-terraform"
    }
  }

  default_tags {
    tags = {
      Project = "kala"
      Env     = var.env
    }
  }
}
