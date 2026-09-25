output "instance_id" {
  description = "Adopted EC2 instance id."
  value       = aws_instance.edge.id
}

output "public_ip" {
  description = "Public IPv4. If this changes, update GitHub secret VPS_HOST by hand before the next CD run. This root does not write GitHub secrets."
  value       = aws_instance.edge.public_ip
}

output "security_group_id" {
  description = "Edge security group id."
  value       = aws_security_group.edge.id
}
