import os

from flask import Flask, jsonify

app = Flask(__name__)

ID_NO = int(os.getenv("NODE_ID", "1"))
PORTA = int(os.getenv("PORT", "5000"))

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)