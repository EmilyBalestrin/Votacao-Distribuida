
# Imagem base do Python
FROM python:3.12-slim

# Define o diretorio de trabalho
WORKDIR /app

# Copia e instala as dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia os arquivos da aplicacao
COPY app/ ./app/

# Porta utilizada pelo Flask
EXPOSE 5000

# Comando para iniciar o servidor
CMD ["python", "app/main.py"]
