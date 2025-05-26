#!/bin/bash

# Parar os containers antigos
echo "Parando containers antigos..."
docker-compose down

# Função de deploy
deploy() {
  echo "Iniciando o deploy..."

    # Faz pull da main via token Fine-grained
    git pull https://github.com/amauricunha/smartnlp.git

  if [ $? -eq 0 ]; then
    echo "Atualização do repositório feita com sucesso."
    # Outras tarefas de deploy, se necessário
  else
    echo "Erro ao fazer o pull do repositório."
    exit 1
  fi
}

# Chama a função de deploy
deploy

# Subir os novos containers
echo "Subindo novos containers..."
docker-compose up -d --build
docker-compose exec backend alembic upgrade head

# Verificar o status
echo "Ambiente atualizado e rodando. Verifique o status dos containers abaixo."
docker-compose ps
