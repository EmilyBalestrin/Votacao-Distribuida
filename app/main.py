import os

from flask import Flask, jsonify
from comunicacao import consultar_no

app = Flask(__name__)

ID_NO = int(os.getenv("NODE_ID", "1"))
PORTA = int(os.getenv("PORT", "5000"))

# Enderecos dos nos definidos por configuracao
ENDERECOS_NOS = {
    1: os.getenv("NO1_URL", "http://localhost:5001"),
    2: os.getenv("NO2_URL", "http://localhost:5002"),
}

@app.route("/")
def inicio():
    return jsonify({
        "mensagem": "Sistema de Votacao Distribuida",
        "no": ID_NO,
        "status": "ativo"
    })

@app.route("/status")
def consultar_status():
    return jsonify({
        "no": ID_NO,
        "status": "ativo"
    })

@app.route("/consultar/<int:id_no>")
def consultar_outro_no(id_no):
    if id_no not in ENDERECOS_NOS:
        return jsonify({
            "erro": "No nao encontrado"
        }), 404

    endereco = ENDERECOS_NOS[id_no]
    resultado = consultar_no(endereco)

    return jsonify({
        "origem": ID_NO,
        "destino": id_no,
        "resposta": resultado
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORTA)