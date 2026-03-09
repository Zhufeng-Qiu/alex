variable "aws_region" {
  description = "AWS region for resources"
  type        = string
}

variable "sagemaker_image_uri" {
  description = "URI of the SageMaker container image (will be auto-generated based on region if not provided)"
  type        = string
  default     = ""
}

variable "embedding_model_name" {
  description = "Name of the HuggingFace model to use"
  type        = string
  default     = "sentence-transformers/all-MiniLM-L6-v2"
}