resource "aws_s3_bucket" "go_trader_s3_bucket" {
  bucket = var.bucket_name
  acl    = var.acl
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

## LAMBDA ##

locals {
  bucket_name          = "go-trader"
  lambda_function_name = "go-trader-function"
  image_name           = "go-trader"
  api_name             = "go-trader-model-api"
  api_path             = "predict"
  image_version        = "latest"
}


data "aws_ecr_repository" "lambda_model_repository" {
  name = local.image_name
}

resource "aws_lambda_function" "lambda_model_function" {
  function_name = local.lambda_function_name

  role = aws_iam_role.lambda_model_role.arn

  # tag is required, "source image ... is not valid" error will pop up
  image_uri    = "${data.aws_ecr_repository.lambda_model_repository.repository_url}:${local.image_version}"
  package_type = "Image"

  # we can check the memory usage in the lambda dashboard, sklearn is a bit memory hungry..
  memory_size = 1024

  environment {
    variables = {
      BUCKET_NAME = local.bucket_name
    }
  }
}


# as per https://learn.hashicorp.com/tutorials/terraform/lambda-api-gateway
# provide role with no access policy initially
resource "aws_iam_role" "lambda_model_role" {
  name = "my-lambda-model-role"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "lambda_model_policy_attachement" {
  role       = aws_iam_role.lambda_model_role.name
  policy_arn = aws_iam_policy.lambda_model_policy.arn
}

resource "aws_iam_policy" "lambda_model_policy" {
  name = "my-lambda-model-policy"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::${local.bucket_name}/*"
    }
  ]
}
EOF
}

resource "aws_api_gateway_rest_api" "lambda_model_api" {
  name = local.api_name
}

resource "aws_api_gateway_resource" "lambda_model_gateway" {
  rest_api_id = aws_api_gateway_rest_api.lambda_model_api.id
  parent_id   = aws_api_gateway_rest_api.lambda_model_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "lambda_model_proxy" {
  rest_api_id   = aws_api_gateway_rest_api.lambda_model_api.id
  resource_id   = aws_api_gateway_resource.lambda_model_gateway.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_model_integration" {
  rest_api_id = aws_api_gateway_rest_api.lambda_model_api.id
  resource_id = aws_api_gateway_method.lambda_model_proxy.resource_id
  http_method = aws_api_gateway_method.lambda_model_proxy.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.lambda_model_function.invoke_arn
}

resource "aws_api_gateway_method" "lambda_model_method" {
  rest_api_id   = aws_api_gateway_rest_api.lambda_model_api.id
  resource_id   = aws_api_gateway_rest_api.lambda_model_api.root_resource_id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_root" {
  rest_api_id = aws_api_gateway_rest_api.lambda_model_api.id
  resource_id = aws_api_gateway_method.lambda_model_method.resource_id
  http_method = aws_api_gateway_method.lambda_model_method.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.lambda_model_function.invoke_arn
}

resource "aws_api_gateway_deployment" "lambda_model_deployment" {
  depends_on = [
    aws_api_gateway_integration.lambda_model_integration,
    aws_api_gateway_integration.lambda_root,
  ]

  rest_api_id = aws_api_gateway_rest_api.lambda_model_api.id
  stage_name  = local.api_path

  # added to stream changes
  stage_description = "deployed at ${timestamp()}"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lambda_permission" "lambda_model_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_model_function.function_name
  principal     = "apigateway.amazonaws.com"

  # The "/*/*" portion grants access from any method on any resource
  # within the API Gateway REST API.
  source_arn = "${aws_api_gateway_rest_api.lambda_model_api.execution_arn}/*/*"
}
