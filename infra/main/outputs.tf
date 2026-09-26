output "instance_id" {
  value = aws_instance.app.id
}

output "public_ip" {
  description = "Point the Cloudflare DNS record here."
  value       = aws_eip.app.public_ip
}

output "connect" {
  description = "Open a shell on the server (needs the Session Manager plugin)."
  value       = "aws ssm start-session --target ${aws_instance.app.id} --region ${var.region} --profile motivetag"
}
