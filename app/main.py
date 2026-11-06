import os

from flask import Flask, jsonify
from comunicacao import consultar_no
from heartbeat import MonitorHeartbeat
from eleicao import EleicaoBully
import threading
import requests
from flask import request
from relogio_lamport import RelogioLamport

app = Flask(__name__)

ID_NO = int(os.getenv("NODE_ID", "1"))
PORTA = int(os.getenv("PORT", "5000"))

# Enderecos dos nos definidos por configuracao
ENDERECOS_NOS = {
    1: os.getenv("NO1_URL", "http://localhost:5001"),
    2: os.getenv("NO2_URL", "http://localhost:5002"),
    3: os.getenv("NO3_URL", "http://localhost:5003"),
}

# Relogio logico independente para cada no
relogio = RelogioLamport()

# Gerenciador de eleicao
eleicao = EleicaoBully(
    id_no=ID_NO,
    enderecos_nos=ENDERECOS_NOS
)


def verificar_mudanca_no(id_no, ativo):
    estado = eleicao.obter_estado()
    lider_atual = estado["lider"]

    # Se o lider caiu, iniciar nova eleicao
    if not ativo and id_no == lider_atual:
        print(
            f"[Sistema] Lider {id_no} indisponivel. "
            "Iniciando nova eleicao.",
            flush=True
        )

        eleicao.iniciar_em_thread()

    # Se um no de prioridade maior retornar,
    # permitir que dispute novamente a lideranca
    elif ativo and lider_atual is not None:
        if id_no > lider_atual:
            print(
                f"[Sistema] No {id_no} retornou. "
                "Iniciando nova eleicao.",
                flush=True
            )

            eleicao.iniciar_em_thread()


# Monitoramento dos servidores
monitor = MonitorHeartbeat(
    id_no=ID_NO,
    enderecos_nos=ENDERECOS_NOS,
    intervalo=3,
    ao_mudar_estado=verificar_mudanca_no
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


@app.route("/relogio", methods=["GET"])
def consultar_relogio():
    return jsonify({
        "no": ID_NO,
        "relogio": relogio.obter_valor()
    })


@app.route("/relogio/evento", methods=["POST"])
def registrar_evento():
    valor = relogio.evento_local()

    print(
        f"[Lamport] No {ID_NO}: evento local, relogio={valor}",
        flush=True
    )

    return jsonify({
        "no": ID_NO,
        "relogio": valor
    })


@app.route("/relogio/enviar/<int:id_destino>", methods=["POST"])
def enviar_evento(id_destino):
    if id_destino not in ENDERECOS_NOS:
        return jsonify({
            "erro": "No de destino desconhecido"
        }), 404

    if id_destino == ID_NO:
        return jsonify({
            "erro": "Escolha outro no"
        }), 400

    # Incrementa o relogio antes do envio
    valor_envio = relogio.enviar_mensagem()

    print(
        f"[Lamport] No {ID_NO}: enviando mensagem "
        f"para No {id_destino}, relogio={valor_envio}",
        flush=True
    )

    try:
        resposta = requests.post(
            f"{ENDERECOS_NOS[id_destino]}/relogio/receber",
            json={
                "origem": ID_NO,
                "relogio": valor_envio
            },
            timeout=3
        )

        resposta.raise_for_status()

        dados_resposta = resposta.json()

        # A resposta tambem e uma mensagem recebida
        valor_resposta = dados_resposta["relogio"]
        novo_valor = relogio.receber_mensagem(
            valor_resposta
        )

        return jsonify({
            "origem": ID_NO,
            "destino": id_destino,
            "relogio_envio": valor_envio,
            "relogio_destino": valor_resposta,
            "relogio_atual": novo_valor
        })

    except (
        requests.RequestException,
        ValueError,
        KeyError,
        TypeError
    ) as erro:
        print(
            f"[Lamport] Falha no envio: {erro}",
            flush=True
        )

        return jsonify({
            "erro": "Nao foi possivel comunicar com o no",
            "destino": id_destino
        }), 503


@app.route("/relogio/receber", methods=["POST"])
def receber_evento():
    dados = request.get_json(silent=True) or {}

    origem = dados.get("origem")
    valor_recebido = dados.get("relogio")

    if (
        type(origem) is not int
        or origem not in ENDERECOS_NOS
        or origem == ID_NO
        or type(valor_recebido) is not int
        or valor_recebido < 0
    ):
        return jsonify({
            "erro": "Mensagem invalida"
        }), 400

    # Atualiza o contador ao receber a mensagem
    novo_valor = relogio.receber_mensagem(
        valor_recebido
    )

    print(
        f"[Lamport] No {ID_NO}: mensagem do No {origem}, "
        f"recebido={valor_recebido}, relogio={novo_valor}",
        flush=True
    )

    # Envia resposta com um novo evento logico
    valor_resposta = relogio.enviar_mensagem()

    return jsonify({
        "no": ID_NO,
        "origem": origem,
        "relogio": valor_resposta
    })

if __name__ == "__main__":
    monitor.iniciar()

    # Aguarda os servidores iniciarem antes da eleicao
    threading.Timer(
        5,
        eleicao.iniciar_em_thread
    ).start()

    app.run(
        host="0.0.0.0",
        port=PORTA,
        debug=False,
        use_reloader=False
    )
