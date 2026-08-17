# EventBridge Scheduler drives the async twin recompute (not in the request path).
resource "aws_scheduler_schedule" "worker" {
  name = "kala-worker-schedule"
  flexible_time_window { mode = "OFF" }
  schedule_expression = var.worker_schedule

  target {
    arn      = aws_lambda_function.worker.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}
