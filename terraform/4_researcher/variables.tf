variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key for the researcher agent"
  type        = string
  sensitive   = true
}

variable "alex_api_endpoint" {
  description = "Alex API endpoint from Part 3"
  type        = string
}

variable "alex_api_key" {
  description = "Alex API key from Part 3"
  type        = string
  sensitive   = true
}

variable "scheduler_enabled" {
  description = "Enable automated research scheduler"
  type        = bool
  default     = false
}

variable "scheduler_schedule" {
  description = "Schedule expression for EventBridge Scheduler. Examples: 'rate(2 hours)', 'rate(1 day)', 'cron(0 9 * * ? *)' (daily at 9 AM UTC), 'cron(0 9 ? * MON *)' (weekly on Monday at 9 AM UTC)"
  type        = string
  default     = "rate(2 hours)"
}