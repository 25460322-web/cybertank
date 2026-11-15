# Tabla de líderes serverless: API Gateway HTTP → Lambda → DynamoDB

resource "aws_dynamodb_table" "puntajes" {
  name         = "${local.nombre}-scores"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "jugador"
  attribute {
    name = "jugador"
    type = "S"
  }
}

data "aws_iam_policy_document" "asumir_lambda" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "leaderboard" {
  name               = "${local.nombre}-leaderboard"
  assume_role_policy = data.aws_iam_policy_document.asumir_lambda.json
}

resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.leaderboard.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "tabla" {
  name = "acceso-tabla"
  role = aws_iam_role.leaderboard.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["dynamodb:UpdateItem", "dynamodb:Scan"]
      Resource = aws_dynamodb_table.puntajes.arn
    }]
  })
}

data "archive_file" "codigo" {
  type        = "zip"
  source_file = "${path.module}/../serverless/lambda_function.py"
  output_path = "${path.module}/build/leaderboard.zip"
}

resource "aws_lambda_function" "leaderboard" {
  function_name    = "${local.nombre}-leaderboard"
  role             = aws_iam_role.leaderboard.arn
  runtime          = "python3.12"
  handler          = "lambda_function.lambda_handler"
  filename         = data.archive_file.codigo.output_path
  source_code_hash = data.archive_file.codigo.output_base64sha256
  memory_size      = 256
  timeout          = 10
  environment {
    variables = { TABLA = aws_dynamodb_table.puntajes.name }
  }
}

resource "aws_apigatewayv2_api" "leaderboard" {
  name          = "${local.nombre}-leaderboard"
  protocol_type = "HTTP"
  target        = aws_lambda_function.leaderboard.arn   # "quick create": ruta $default + etapa automática
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST"]
    allow_headers = ["content-type"]
  }
}

resource "aws_lambda_permission" "api" {
  statement_id  = "PermitirApiGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.leaderboard.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.leaderboard.execution_arn}/*"
}
