#!/bin/bash

echo "Gerando certificado autoassinado para ambiente de desenvolvimento..."
openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365 -subj "/C=BR/ST=SP/L=Sao Paulo/O=Mentory/CN=localhost"
echo "Certificado (cert.pem) e chave privada (key.pem) gerados com sucesso na raiz do projeto."
