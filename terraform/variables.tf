variable "bucket_name" {
  type        = string
  description = "(required since we are not using 'bucket') Creates a unique bucket name beginning with the specified prefix. Conflicts with bucket."
  default     = "go-trader"
}
variable "acl" {
  type        = string
  description = "(Optional) The canned ACL to apply. Defaults to private. Conflicts with grant."
  default     = "private"
}
variable "versioning" {
  type        = bool
  description = "(Optional) A state of versioning."
  default     = true
}
variable "kms_master_key_id" {
  type        = string
  description = "(optional) The AWS KMS master key ID used for the SSE-KMS encryption. This can only be used when you set the value of sse_algorithm as aws:kms. The default aws/s3 AWS KMS master key is used if this element is absent while the sse_algorithm is aws:kms."
  default     = "aws/s3"
}
variable "sse_algorithm" {
  type        = string
  description = "(required) The server-side encryption algorithm to use. Valid values are AES256 and aws:kms"
  default     = "aws:kms"
}
variable "aws_region" {
  type        = string
  description = "The region to use"
  default     = "us-east-1"
}
variable "tags" {
  type        = map
  description = "(Optional) A mapping of tags to assign to the bucket."
  default = {
    environment = "prod"
    terraform   = "true"
  }
}
variable "lambda_function_name" {
  type        = string
  description = "function"
  default     = "go-trader-function"
}
variable "image_name" {
  type        = string
  description = "image name"
  default     = "go-trader"
}
variable "image_version" {
  type        = string
  description = "image version"
  default     = "latest"
}
