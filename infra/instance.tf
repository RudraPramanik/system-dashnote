resource "aws_instance" "edge" {
  ami                         = var.ami_id
  instance_type               = var.instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.edge.id]
  key_name                    = var.key_name != "" ? var.key_name : null
  associate_public_ip_address = var.associate_public_ip

  lifecycle {
    # AMI and user_data mismatches force replacement. Ignore them so import
    # can adopt the running box. Align other fields in tfvars instead.
    ignore_changes = [ami, user_data]
  }

  tags = {
    Name = "${var.name_prefix}-edge"
  }
}

resource "aws_eip" "edge" {
  count  = var.manage_eip ? 1 : 0
  domain = "vpc"

  tags = {
    Name = "${var.name_prefix}-edge"
  }
}

resource "aws_eip_association" "edge" {
  count         = var.manage_eip ? 1 : 0
  instance_id   = aws_instance.edge.id
  allocation_id = aws_eip.edge[0].id
}
