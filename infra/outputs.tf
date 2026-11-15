output "cluster" {
  value = module.eks.cluster_name
}

output "registro" {
  value = aws_ecr_repository.servidor.repository_url
}

output "leaderboard_url" {
  value = aws_apigatewayv2_api.leaderboard.api_endpoint
}

output "conectar_kubectl" {
  value = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
}
