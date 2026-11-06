import os

from flask import Flask, jsonify
from comunicacao import consultar_no
from heartbeat import MonitorHeartbeat
from eleicao import EleicaoBully

app = Flask(__name__)

ID_NO = int(os.getenv("NODE_ID", "1"))
PORTA = int(os.getenv("PORT", "5000"))

# Enderecos dos nos definidos por configuracao
ENDERECOS_NOS = {
    1: os.getenv("NO1_URL", "http://localhost:5001"),
    2: os.getenv("NO2_URL", "http://localhost:5002"),
    3: os.getenv("NO3_URL", "http://localhost:5003"),
}

monitor = MonitorHeartbeat(
    id_no=ID_NO,
    enderecos_nos=ENDERECOS_NOS,
    intervalo=3
)

eleicao = EleicaoBully(
    id_no=ID_NO,
    enderecos_nos=ENDERECOS_NOS
)

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

@app.route("/nos")
def listar_nos():
    return jsonify({
        "no_atual": ID_NO,
        "nos": monitor.obter_estados()
    })


@app.route("/lider")
def consultar_lider():
    return jsonify(eleicao.obter_estado())


@app.route("/eleicao/iniciar", methods=["POST"])
def iniciar_eleicao():
    iniciada = eleicao.iniciar_em_thread()

    return jsonify({
        "no": ID_NO,
        "eleicao_iniciada": iniciada
    })


@app.route("/eleicao", methods=["POST"])
def receber_eleicao():
    from flask import request

    dados = request.get_json(silent=True) or {}
    origem = dados.get("origem")

    if not isinstance(origem, int) or origem not in ENDERECOS_NOS:
        return jsonify({"erro": "Origem invalida"}), 400

    aceita = eleicao.receber_eleicao(origem)

    if not aceita:
        return jsonify({"erro": "Prioridade invalida"}), 400

    return jsonify({
        "no": ID_NO,
        "resposta": "OK"
    })


@app.route("/coordenador", methods=["POST"])
def receber_coordenador():
    from flask import request

    dados = request.get_json(silent=True) or {}
    id_lider = dados.get("lider")

    if not isinstance(id_lider, int):
        return jsonify({"erro": "Lider invalido"}), 400

    if not eleicao.receber_coordenador(id_lider):
        return jsonify({"erro": "Lider desconhecido"}), 400

    return jsonify({
        "no": ID_NO,
        "lider": id_lider
    })

if __name__ == "__main__":
    monitor.iniciar()

    app.run(
        host="0.0.0.0",
        port=PORTA,
        debug=False,
        use_reloader=False
    )