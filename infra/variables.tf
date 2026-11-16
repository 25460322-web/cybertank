variable "region" {
  type    = string
  default = "us-east-2"
}

variable "version_k8s" {
  description = "Versión de Kubernetes de EKS (debe estar soportada por tu versión de Agones)"
  type        = string
  default     = "1.33"
}

variable "tipo_instancia" {
  description = "Tipo de máquina de los nodos de servidores de juego"
  type        = string
  default     = "c7i-flex.large" # la cuenta está en plan gratuito: solo tipos free-tier-eligible
}

variable "rol_github_arn" {
  description = "ARN del rol github-deployer (práctica 3.2); vacío = sin acceso del pipeline"
  type        = string
  default     = ""
}

variable "nodos_min" {
  type    = number
  default = 3
}

variable "nodos_max" {
  type    = number
  default = 12
}
