# Zero-cost monitoring (docs/adr/0006, 0017): SNS e-mail (free at this volume) for the
# backup, restore-drill and disk alerts sent by deploy/backup.sh and restore_drill.sh.
# The EC2 status and CPU alarms went with the server; the Pi is watched by Grafana
# Cloud (if set up) and an outside uptime check on /healthz (infra/README.md).

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
