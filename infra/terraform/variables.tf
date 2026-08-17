variable "region" {
  type    = string
  default = "ap-southeast-1"
}

variable "env" {
  type    = string
  default = "pilot"
}

variable "assume_role_arn" {
  type        = string
  default     = ""
  description = "Cross-account role ARN from the school's AWS Organization, if provided."
}

variable "api_image_uri" {
  type        = string
  description = "ECR image URI for the FastAPI backend (repo:tag)."
}

variable "worker_image_uri" {
  type        = string
  description = "ECR image URI for the async worker."
}

variable "frontend_url" {
  type        = string
  description = "Origin of the deployed SPA, used for CORS and the launch redirect."
}

variable "worker_schedule" {
  type        = string
  default     = "rate(15 minutes)"
  description = "EventBridge Scheduler expression for the twin recompute worker."
}

variable "budget_alert_email" {
  type        = string
  default     = ""
  description = "Email for a monthly cost alert. Empty disables the budget."
}
