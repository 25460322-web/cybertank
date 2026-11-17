provider "helm" {
  kubernetes {
    host                   = module.eks.cluster_endpoint
    cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)
    exec {
      api_version = "client.authentication.k8s.io/v1beta1"
      command     = "aws"
      args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name, "--region", var.region]
    }
  }
}

# ---------------------------------------------------------------- Agones
resource "helm_release" "agones" {
  name             = "agones"
  repository       = "https://agones.dev/chart/stable"
  chart            = "agones"
  version          = "1.59.0" # última con soporte para Kubernetes 1.33
  namespace        = "agones-system"
  create_namespace = true
  timeout          = 600 # el balanceador del allocator tarda más de los 5 min por omisión
  depends_on       = [module.eks]

  # El ping UDP pide un LoadBalancer UDP; el balanceador clásico de EKS no lo soporta y se
  # queda en <pending> para siempre (Helm nunca termina de esperar). El juego no lo usa.
  set {
    name  = "agones.ping.udp.expose"
    value = "false"
  }
}

# ---------------------------------------------------------------- Cluster Autoscaler (capa de nodos)
# Sin IRSA (OIDC bloqueado por la SCP): la política va en el rol de los nodos (ver eks.tf).
resource "aws_iam_policy" "autoscaler" {
  name = "${local.nombre}-cluster-autoscaler"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "autoscaling:DescribeAutoScalingGroups", "autoscaling:DescribeAutoScalingInstances",
          "autoscaling:DescribeLaunchConfigurations", "autoscaling:DescribeScalingActivities",
          "autoscaling:DescribeTags", "ec2:DescribeImages", "ec2:DescribeInstanceTypes",
          "ec2:DescribeLaunchTemplateVersions", "ec2:GetInstanceTypesFromInstanceRequirements",
          "eks:DescribeNodegroup"
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["autoscaling:SetDesiredCapacity", "autoscaling:TerminateInstanceInAutoScalingGroup"]
        Resource = "*"
        Condition = {
          StringEquals = { "aws:ResourceTag/k8s.io/cluster-autoscaler/${local.nombre}" = "owned" }
        }
      }
    ]
  })
}

resource "helm_release" "cluster_autoscaler" {
  name       = "cluster-autoscaler"
  repository = "https://kubernetes.github.io/autoscaler"
  chart      = "cluster-autoscaler"
  namespace  = "kube-system"
  depends_on = [module.eks]

  set {
    name  = "autoDiscovery.clusterName"
    value = module.eks.cluster_name
  }
  set {
    name  = "awsRegion"
    value = var.region
  }
  set {
    name  = "image.tag"
    value = "v1.33.6" # debe coincidir con var.version_k8s
  }
}
