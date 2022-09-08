terraform {
  required_version = ">= 1.0.8"
  required_providers {
    aws = {
      version = ">= 3.38.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.2.0"
    }
  }
}
