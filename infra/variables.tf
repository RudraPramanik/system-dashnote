variable "region" {
  type        = string
  description = "AWS region of the existing edge instance."
}

variable "name_prefix" {
  type        = string
  description = "Tag prefix for the adopted edge resources."
  default     = "dashnote"
}

variable "instance_type" {
  type        = string
  description = "Must match the live instance (t3.small today)."
  default     = "t3.small"
}

variable "ami_id" {
  type        = string
  description = "AMI id from the A0 inventory. Ignored after import so a mismatch cannot replace the instance."
}

variable "vpc_id" {
  type        = string
  description = "VPC id of the live security group."
}

variable "subnet_id" {
  type        = string
  description = "Subnet id of the live instance."
}

variable "security_group_name" {
  type        = string
  description = "Exact name of the live security group. Must match before import."
}

variable "key_name" {
  type        = string
  description = "Optional EC2 key pair name. Empty string omits it."
  default     = ""
}

variable "allowed_ssh_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to SSH (22). Prefer your current IP, not 0.0.0.0/0."
}

variable "allowed_http_cidrs" {
  type        = list(string)
  description = "CIDRs allowed to HTTP (80)."
}

variable "associate_public_ip" {
  type        = bool
  description = "Must match the live instance. Wrong value can force replacement — abort that plan."
  default     = true
}

variable "manage_eip" {
  type        = bool
  description = "True only when an Elastic IP is already in use (or you are deliberately attaching one). Import it; do not apply a create against the live box."
  default     = false
}
