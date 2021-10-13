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

data "aws_ecr_repository" "lambda_model_repository" {
  name = var.image_name
}

resource "aws_lambda_function" "lambda_model_function" {
  function_name = var.lambda_function_name

  role = aws_iam_role.lambda_model_role.arn

  # tag is required, "source image ... is not valid" error will pop up
  image_uri    = "${data.aws_ecr_repository.lambda_model_repository.repository_url}:${var.image_version}"
  package_type = "Image"

  # we can check the memory usage in the lambda dashboard, sklearn is a bit memory hungry..
  memory_size = 10240
  timeout     = 900 # 15 minutes

  environment {
    variables = {
      BUCKET_NAME = var.bucket_name
    }
  }

  file_system_config {
    # EFS file system access point ARN
    arn = aws_efs_access_point.access_point_for_lambda.arn

    # Local mount path inside the lambda function. Must start with '/mnt/'.
    local_mount_path = "/mnt/shared-storage"
  }

  vpc_config {
    # Every subnet should be able to reach an EFS mount target in the same Availability Zone. Cross-AZ mounts are not permitted.
    subnet_ids         = [aws_subnet.private_subnet.id]
    security_group_ids = [aws_default_security_group.sg_for_lambda.id]
  }

  # Explicitly declare dependency on EFS mount target.
  # When creating or updating Lambda functions, mount target must be in 'available' lifecycle state.
  depends_on = [aws_efs_mount_target.alpha]
}

## VPC ## 
resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "public_subnet" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.0.0/21"

  tags = {
    Name = "go-trader-subnet-public"
  }
}

resource "aws_subnet" "private_subnet" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.8.0/21"
  map_public_ip_on_launch = false
  tags = {
    Name = "go-trader-subnet-private"
  }
}


resource "aws_route_table" "route_table_private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat_gateway.id
  }

  tags = {
    Name = "go-trader-route-table-private"
  }
}

resource "aws_route_table_association" "route_table_association_private" {
  subnet_id      = aws_subnet.private_subnet.id
  route_table_id = aws_route_table.route_table_private.id
}

resource "aws_internet_gateway" "internet_gateway" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "go-trader-internet-gateway"
  }
}


resource "aws_route_table" "route_table_public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.internet_gateway.id
  }

  tags = {
    Name = "go-trader-route-table-public"
  }
}

resource "aws_route_table_association" "route_table_association_public" {
  subnet_id      = aws_subnet.public_subnet.id
  route_table_id = aws_route_table.route_table_public.id
}

resource "aws_eip" "eip" {
  vpc        = true
  depends_on = [aws_internet_gateway.internet_gateway]
  tags = {
    Name = "go-trader-eip"
  }
}

resource "aws_nat_gateway" "nat_gateway" {
  allocation_id = aws_eip.eip.id
  subnet_id     = aws_subnet.public_subnet.id

  tags = {
    Name = "go-trader-nat-gateway"
  }
}

resource "aws_default_network_acl" "default_network_acl" {
  default_network_acl_id = aws_vpc.main.default_network_acl_id
  subnet_ids             = [aws_subnet.public_subnet.id, aws_subnet.private_subnet.id]

  ingress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  egress {
    protocol   = -1
    rule_no    = 100
    action     = "allow"
    cidr_block = "0.0.0.0/0"
    from_port  = 0
    to_port    = 0
  }

  tags = {
    Name = "go-trader-default-network-acl"
  }
}

resource "aws_default_security_group" "sg_for_lambda" {
  vpc_id = aws_vpc.main.id

  ingress {
    protocol  = -1
    self      = true
    from_port = 0
    to_port   = 0
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "go-trader-default-security-group"
  }
}

## EFS ##
resource "aws_efs_file_system" "efs_for_lambda" {
  tags = {
    Name = "efs_for_lambda"
  }
}

# Mount target connects the file system to the subnet
resource "aws_efs_mount_target" "alpha" {
  file_system_id  = aws_efs_file_system.efs_for_lambda.id
  subnet_id       = aws_subnet.public_subnet.id
  security_groups = [aws_default_security_group.sg_for_lambda.id]
}

# EFS access point used by lambda file system
resource "aws_efs_access_point" "access_point_for_lambda" {
  file_system_id = aws_efs_file_system.efs_for_lambda.id

  root_directory {
    path = "/shared-storage"
    creation_info {
      owner_gid   = 1000
      owner_uid   = 1000
      permissions = "777"
    }
  }

  posix_user {
    gid = 1000
    uid = 1000
  }
}

## IAM ##


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

resource "aws_iam_role_policy_attachment" "iam_role_policy_attachment_lambda_vpc_access_execution" {
  role       = aws_iam_role.lambda_model_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
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
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::${var.bucket_name}/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": ["arn:aws:s3:::${var.bucket_name}"]
    },
    {
        "Effect": "Allow",
        "Action": [
            "kms:Decrypt",
            "kms:GenerateDataKey"
        ],
        "Resource": "*"
    },
    {
        "Effect": "Allow",
        "Action" :["ssm:DescribeParameters"],
        "Resource": ["*"]
    },
    {
        "Effect": "Allow",
        "Action": [
            "ssm:GetParameter",
            "ssm:GetParametersByPath"
        ],
        "Resource":  ["arn:aws:ssm:*:*:parameter/", "arn:aws:ssm:*:*:parameter/*"]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeInstances",
        "ec2:AttachNetworkInterface"
      ],
      "Resource": "*"
    }
  ]
}
EOF
}

## CLOUDWATCH TRIGGERS ##

resource "aws_cloudwatch_event_rule" "every_day_btc" {
  name                = "every-day-btc"
  description         = "Fires every day for btc"
  schedule_expression = "rate(1 day)"
}

resource "aws_cloudwatch_event_target" "check_btc_every_day" {
  rule      = aws_cloudwatch_event_rule.every_day_btc.name
  target_id = "check_btc_predictions"
  arn       = aws_lambda_function.lambda_model_function.arn
  input     = "{\"coinToPredict\": \"btc\"}"
}

resource "aws_lambda_permission" "allow_cloudwatch_to_call_lambda_model_function" {
  statement_id  = "AllowExecutionFromCloudWatch"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.lambda_model_function.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.every_day_btc.arn
}
