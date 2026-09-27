# Zero-cost monitoring (docs/adr/0006): EC2's free basic metrics, alarms within the
# CloudWatch free tier, and SNS e-mail (also free at this volume). Uptime is checked
# by a scheduled GitHub Actions workflow (.github/workflows/uptime.yml); backup
# failures are e-mailed by deploy/backup.sh through the same topic.

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email == null ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# deploy.sh writes this into the server's .env as ALERT_TOPIC_ARN.
resource "aws_ssm_parameter" "alert_topic" {
  name  = "/${var.project}/alert-topic-arn"
  type  = "String"
  value = aws_sns_topic.alerts.arn
}

locals {
  instance = { InstanceId = aws_instance.app.id }
  alerts   = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project}-cpu-high"
  alarm_description   = "CPU above 80% for 15 minutes."
  namespace           = "AWS/EC2"
  metric_name         = "CPUUtilization"
  dimensions          = local.instance
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 80
  alarm_actions       = local.alerts
  ok_actions          = local.alerts
}

# A failed host is moved to healthy hardware automatically (same ID, IP and volumes).
resource "aws_cloudwatch_metric_alarm" "system_check" {
  alarm_name          = "${var.project}-system-check-failed"
  alarm_description   = "AWS hardware or network problem; the instance is being recovered."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_System"
  dimensions          = local.instance
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  alarm_actions       = concat(local.alerts, ["arn:aws:automate:${var.region}:ec2:recover"])
  ok_actions          = local.alerts
}

resource "aws_cloudwatch_metric_alarm" "instance_check" {
  alarm_name          = "${var.project}-instance-check-failed"
  alarm_description   = "The OS is not responding (out of memory, kernel problem); rebooting."
  namespace           = "AWS/EC2"
  metric_name         = "StatusCheckFailed_Instance"
  dimensions          = local.instance
  statistic           = "Maximum"
  period              = 60
  evaluation_periods  = 3
  comparison_operator = "GreaterThanOrEqualToThreshold"
  threshold           = 1
  alarm_actions       = concat(local.alerts, ["arn:aws:automate:${var.region}:ec2:reboot"])
  ok_actions          = local.alerts
}
