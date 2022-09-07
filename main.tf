resource "aws_sns_topic" "this" {
  name         = "${var.name}-slack-notify"
  display_name = "Autoscaling Notifications to Slack"
}

resource "aws_sns_topic_policy" "sns_topic_policy" {
  count = var.aux_sns_senders_arn_list == null ? 0 : 1

  arn    = aws_sns_topic.this.arn
  policy = data.aws_iam_policy_document.sns_topic_policy[count.index].json
}

# Access from a domestic account won't affected by the policy
data "aws_iam_policy_document" "sns_topic_policy" {
  // Keep default policy on cloud untouched. Remove it after Automation will be migrated to another account on all environments
  count = var.aux_sns_senders_arn_list == null ? 0 : 1

  // TODO: make this statement dependent on var.aux_sns_senders_arn_list after Automation will be migrated to another account on all environments
  statement {
    sid = "AllowPublishFromAnotherAccounts"
    principals {
      type        = "AWS"
      identifiers = ["*"]
    }
    effect    = "Allow"
    actions   = ["SNS:Publish"]
    resources = [aws_sns_topic.this.arn]
    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = var.aux_sns_senders_arn_list
    }
  }

  // TODO: make this statement mandatory after Automation will be migrated to another account on all environments
  // When you create a CW Events rule with Amazon SNS as the target, CW Events adds the permission to your Amazon SNS
  // topic on your behalf, so we should do it explicitly here
  statement {
    sid = "AllowPublishFromCloudWatchEventsRules"
    principals {
      type = "Service"
      identifiers = [
        "events.amazonaws.com",
        "cloudwatch.amazonaws.com",
      ]
    }
    effect    = "Allow"
    actions   = ["SNS:Publish"]
    resources = [aws_sns_topic.this.arn]
  }
}

resource "aws_iam_role" "this" {
  name = "${var.name}-slack-notify"

  assume_role_policy = <<EOT
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": "sts:AssumeRole",
            "Principal": {
              "Service": "lambda.amazonaws.com"
            },
            "Effect": "Allow",
            "Sid": ""
        }
    ]
}
EOT
}

resource "aws_iam_role_policy" "this" {
  name = "${var.name}-slack-notify"
  role = aws_iam_role.this.id

  policy = <<EOT
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents",
                "ecs:DescribeServices"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
EOT
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${local.lambda_slack_notify_name}"
  retention_in_days = 7
}

data "archive_file" "this" {
  source_file      = "${path.module}/source/lambda_function/main.py"
  output_path      = "${local.lambda_slack_notify_name}.zip"
  output_file_mode = "0666"
  type             = "zip"
}

resource "aws_lambda_function" "this" {
  count            = var.enable_lambda ? 1 : 0
  function_name    = local.lambda_slack_notify_name
  role             = aws_iam_role.this.arn
  handler          = "main.lambda_handler"
  runtime          = var.runtime
  timeout          = var.timeout
  filename         = data.archive_file.this.output_path
  source_code_hash = data.archive_file.this.output_base64sha256
  layers           = var.layers

  environment {
    variables = {
      SLACK_CHANNEL  = var.slack_channel
      SLACK_USERNAME = var.slack_username
      SLACK_WEBHOOK  = var.slack_webhook
      STACK_NAME     = var.name
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.this
  ]
}

resource "aws_lambda_permission" "this" {
  count = var.enable_lambda ? 1 : 0

  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this[0].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.this.arn
}

resource "aws_sns_topic_subscription" "lambda-sns" {
  count = var.enable_lambda ? 1 : 0

  topic_arn = aws_sns_topic.this.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.this[0].arn
}
