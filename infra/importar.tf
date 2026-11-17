# El repositorio ECR ya existe desde la práctica 3.3: se trae al estado en vez de recrearlo.
# (`terraform import` por comando falla aquí porque el proveedor helm depende de un clúster
#  que aún no existe; el bloque import lo resuelve dentro del plan.)
import {
  to = aws_ecr_repository.servidor
  id = "cybertank-server"
}
