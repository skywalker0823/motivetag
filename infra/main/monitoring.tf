# Alarms e-mail var.alert_email through SNS. Uptime is checked from outside by a
# Route 53 health check, whose metrics only exist in us-east-1, so it has its own
# topic there. Application errors go to Sentry (see api/__init__.py).

resource "aws_sns_topic" "alerts" {
  name = "${var.project}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email == null ? 0 : 1
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic" "alerts_us_east_1" {
  provider = aws.us_east_1
  name     = "${var.project}-alerts"
}

resource "aws_sns_topic_subscription" "alerts_us_east_1_email" {
  provider  = aws.us_east_1
  count     = var.alert_email == null ? 0 : 1
  topic_arn = aws_sns_topic.alerts_us_east_1.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# --- Uptime: probes https://<domain>/healthz through Cloudflare from several regions.

resource "aws_route53_health_check" "site" {
  fqdn              = var.domain
  port              = 443
  type              = "HTTPS" # 2xx/3xx is healthy; string matching would cost extra
  resource_path     = "/healthz"
  enable_sni        = true
  request_interval  = 30
  failure_threshold = 3

  tags = {
    Name = "${var.project}-site"
  }
}

resource "aws_cloudwatch_metric_alarm" "site_down" {
  provider            = aws.us_east_1
  alarm_name          = "${var.project}-site-down"
  alarm_description   = "https://${var.domain}/healthz is failing from the Route 53 health checkers."
  namespace           = "AWS/Route53"
  metric_name         = "HealthCheckStatus"
  dimensions          = { HealthCheckId = aws_route53_health_check.site.id }
  statistic           = "Minimum"
  period              = 60
  evaluation_periods  = 2
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts_us_east_1.arn]
  ok_actions          = [aws_sns_topic.alerts_us_east_1.arn]
}

# --- Server: CPU and status checks come from EC2; disk and memory from the
# CloudWatch agent, which Systems Manager installs and configures.

resource "aws_ssm_parameter" "cloudwatch_agent" {
  # CloudWatchAgentServerPolicy can read parameters named AmazonCloudWatch-*.
  name = "AmazonCloudWatch-${var.project}"
  type = "String"
  value = jsonencode({
    agent = {
      metrics_collection_interval = 60
      omit_hostname               = true
    }
    metrics = {
      append_dimensions = { InstanceId = "$${aws:InstanceId}" }
      # Publishes disk metrics with exactly these dimensions, which the alarms use.
      aggregation_dimensions = [["InstanceId", "path"]]
      metrics_collected = {
        disk = {
          measurement = ["used_percent"]
          resources   = ["/", "/srv/motivetag"]
          drop_device = true
        }
        mem  = { measurement = ["mem_used_percent"] }
        swap = { measurement = ["swap_used_percent"] }
      }
    }
  })
}

resource "aws_ssm_association" "cloudwatch_agent_install" {
  association_name    = "${var.project}-cloudwatch-agent-install"
  name                = "AWS-ConfigureAWSPackage"
  schedule_expression = "rate(7 days)"
  parameters = {
    action = "Install"
    name   = "AmazonCloudWatchAgent"
  }
  targets {
    key    = "InstanceIds"
    values = [aws_instance.app.id]
  }
}

resource "aws_ssm_association" "cloudwatch_agent_config" {
  association_name = "${var.project}-cloudwatch-agent-config"
  name             = "AmazonCloudWatch-ManageAgent"
  # Also re-applies the config daily, which covers a first run that raced the install.
  schedule_expression = "rate(1 day)"
  parameters = {
    action                        = "configure"
    mode                          = "ec2"
    optionalConfigurationSource   = "ssm"
    optionalConfigurationLocation = aws_ssm_parameter.cloudwatch_agent.name
    optionalRestart               = "yes"
  }
  targets {
    key    = "InstanceIds"
    values = [aws_instance.app.id]
  }
  depends_on = [aws_ssm_association.cloudwatch_agent_install]
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

resource "aws_cloudwatch_metric_alarm" "disk" {
  for_each = {
    root = "/"
    data = "/srv/motivetag"
  }
  alarm_name          = "${var.project}-disk-${each.key}"
  alarm_description   = "${each.value} is more than 85% full."
  namespace           = "CWAgent"
  metric_name         = "disk_used_percent"
  dimensions          = merge(local.instance, { path = each.value })
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  comparison_operator = "GreaterThanThreshold"
  threshold           = 85
  treat_missing_data  = "breaching" # no data means the agent is down
  alarm_actions       = local.alerts
  ok_actions          = local.alerts
}

resource "aws_cloudwatch_metric_alarm" "memory" {
  alarm_name          = "${var.project}-memory-high"
  alarm_description   = "Memory above 90% for 15 minutes."
  namespace           = "CWAgent"
  metric_name         = "mem_used_percent"
  dimensions          = local.instance
  statistic           = "Average"
  period              = 300
  evaluation_periods  = 3
  comparison_operator = "GreaterThanThreshold"
  threshold           = 90
  alarm_actions       = local.alerts
  ok_actions          = local.alerts
}

# --- Backups: deploy/backup.sh and deploy/restore_drill.sh publish these.

resource "aws_cloudwatch_metric_alarm" "backup_missing" {
  alarm_name          = "${var.project}-backup-missing"
  alarm_description   = "No successful MySQL backup in the last 24 hours (journalctl -u motivetag-backup)."
  namespace           = var.project
  metric_name         = "BackupSuccess"
  statistic           = "Maximum"
  period              = 86400
  evaluation_periods  = 1
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "breaching"
  alarm_actions       = local.alerts
  ok_actions          = local.alerts
}

resource "aws_cloudwatch_metric_alarm" "restore_drill_failed" {
  alarm_name          = "${var.project}-restore-drill-failed"
  alarm_description   = "The weekly restore drill failed (journalctl -u motivetag-restore-drill)."
  namespace           = var.project
  metric_name         = "RestoreDrillSuccess"
  statistic           = "Minimum"
  period              = 86400
  evaluation_periods  = 1
  comparison_operator = "LessThanThreshold"
  threshold           = 1
  treat_missing_data  = "notBreaching"
  alarm_actions       = local.alerts
}
