data "aws_availability_zones" "disponibles" {
  state = "available"
}

# VPC con subredes públicas: los nodos reciben IP pública y los jugadores se conectan
# directamente al puerto del GameServer (7000-8000). Sin NAT Gateway para ahorrar.
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name                    = local.nombre
  cidr                    = "10.0.0.0/16"
  azs                     = slice(data.aws_availability_zones.disponibles.names, 0, 2)
  public_subnets          = ["10.0.1.0/24", "10.0.2.0/24"]
  map_public_ip_on_launch = true
  enable_nat_gateway      = false

  public_subnet_tags = { "kubernetes.io/role/elb" = 1 }
}
