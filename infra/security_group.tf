resource "aws_security_group" "edge" {
  name        = var.security_group_name
  description = "DashNote thin VPS edge. SSH and HTTP only; API 8000 stays unpublished."
  vpc_id      = var.vpc_id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.allowed_ssh_cidrs
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.allowed_http_cidrs
  }

  # Port 8000 is intentionally absent. Nginx publishes :80; the API stays on the Docker network.

  egress {
    description = "Hosted data plane, registries, and LLM APIs"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.name_prefix}-edge"
  }
}
