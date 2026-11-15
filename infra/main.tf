terraform {
  required_version = ">= 1.10"
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.95" }
    helm    = { source = "hashicorp/helm", version = "~> 2.17" }
    archive = { source = "hashicorp/archive", version = "~> 2.7" }
  }
  # Estado remoto en S3 con bloqueo nativo (use_lockfile) para trabajar en equipo.
  backend "s3" {
    bucket       = "cybertank-tfstate-<TU-ID>"
    key          = "cybertank/terraform.tfstate"
    region       = "us-east-2"
    encrypt      = true
    use_lockfile = true
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Proyecto = "cybertank", Entorno = terraform.workspace, Gestionado = "terraform" }
  }
}

locals {
  nombre = "cybertank-${terraform.workspace}"   # cybertank-default, cybertank-prod, ...
}
