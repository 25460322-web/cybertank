module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name                             = local.nombre
  cluster_version                          = var.version_k8s
  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true

  # Laboratorio: sin llave KMS ni logs del plano de control (evita costos y restos al destruir)
  create_kms_key              = false
  cluster_encryption_config   = {}
  create_cloudwatch_log_group = false
  cluster_enabled_log_types   = []

  # Permite que el pipeline de GitHub Actions (práctica 3.2) actualice la flota
  access_entries = var.rol_github_arn == "" ? {} : {
    github = {
      principal_arn = var.rol_github_arn
      policy_associations = {
        admin = {
          policy_arn   = "arn:aws:eks::aws:cluster-access-policy/AmazonEKSClusterAdminPolicy"
          access_scope = { type = "cluster" }
        }
      }
    }
  }

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnets

  eks_managed_node_groups = {
    juego = {
      instance_types = [var.tipo_instancia]
      min_size       = var.nodos_min
      max_size       = var.nodos_max
      desired_size   = var.nodos_min
      labels         = { rol = "juego" }
    }
  }

  node_security_group_additional_rules = {
    partidas_tcp = {
      description = "Jugadores -> GameServers (WebSocket)"
      type        = "ingress"
      protocol    = "tcp"
      from_port   = 7000
      to_port     = 8000
      cidr_blocks = ["0.0.0.0/0"]
    }
    partidas_udp = {
      description = "Jugadores -> GameServers (UDP)"
      type        = "ingress"
      protocol    = "udp"
      from_port   = 7000
      to_port     = 8000
      cidr_blocks = ["0.0.0.0/0"]
    }
    plano_control = {
      description                   = "Plano de control -> webhooks de Agones"
      type                          = "ingress"
      protocol                      = "-1"
      from_port                     = 0
      to_port                       = 0
      source_cluster_security_group = true
    }
  }
}

resource "aws_ecr_repository" "servidor" {
  name                 = "cybertank-server"
  image_tag_mutability = "MUTABLE"
  force_delete         = true   # terraform destroy borra también las imágenes
}
