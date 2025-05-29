#!/bin/bash
set -e
SSL_DIR="./ssl"
CRT="$SSL_DIR/nginx.crt"
KEY="$SSL_DIR/nginx.key"

mkdir -p "$SSL_DIR"

if [ ! -f "$CRT" ] || [ ! -f "$KEY" ]; then
  echo "Gerando certificado SSL self-signed em $SSL_DIR ..."
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "$KEY" -out "$CRT" \
    -subj "/CN=localhost"
  echo "Certificado gerado: $CRT"
else
  echo "Certificado SSL já existe em $SSL_DIR"
fi
