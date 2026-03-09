variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "bedrock_regions" {
  description = "AWS regions for Bedrock (align with 6_agents; AWS may route inference across these US regions)"
  type        = list(string)
  default     = ["us-east-1", "us-east-2", "us-west-1", "us-west-2"]
}

variable "bedrock_model_id" {
  description = "Bedrock model ID to monitor (e.g., amazon.nova-pro-v1:0)"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}