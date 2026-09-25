terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
  }

  # Partial backend. Bucket, region, and lock table come from a gitignored
  # backend.hcl (see backend.hcl.example). encrypt stays on here.
  # Validate without AWS state: terraform init -backend=false
  backend "s3" {
    key     = "level-a/edge.tfstate"
    encrypt = true
  }
}

provider "aws" {
  region = var.region
}
