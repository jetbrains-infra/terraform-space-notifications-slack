locals {
  lambda_slack_notify_name = "${var.name}-slack-notify"
}
variable "enable_lambda" {
  type = bool
}
variable "name" {}
variable "slack_channel" {}
variable "slack_username" {}
variable "slack_webhook" {}

variable "runtime" {
  description = "Lambda Function runtime"
  type        = string
  default     = "python3.9"
}

variable "timeout" {
  description = "The amount of time your Lambda Function has to run in seconds."
  type        = number
  default     = 300
}

variable "layers" {
  description = "List of Lambda Layer Version ARNs (maximum of 5) to attach to your Lambda Function."
  type        = list(string)
  default     = null
}

variable "aux_sns_senders_arn_list" {
  description = "List of ARNs allowed to send a messages to the SNS. It may me useful with access from another AWS account. A default SNS policy will be applied if the list is not specified."
  type        = list(string)
  default     = null
}
