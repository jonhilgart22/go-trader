resource "aws_s3_bucket" "go_trader_s3_bucket" {
  bucket = var.bucket_name
  acl           = var.acl
  versioning {
    enabled = var.versioning
  }
  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        kms_master_key_id = var.kms_master_key_id
        sse_algorithm     = var.sse_algorithm
      }
    }
  }
  tags = var.tags
}
