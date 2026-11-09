import os

from comunicacao import consultar_no
from heartbeat import MonitorHeartbeat
from eleicao import EleicaoBully
import threading
import requests
from relogio_lamport import RelogioLamport
from persistencia import Persistencia
from replicacao import enviar_operacao
from recuperacao import coletar_estados, comparar_estados
from flask import Flask, jsonify, request, render_template
import threading
import time
app = Flask(__name__)

ID_NO = int(os.getenv("NODE_ID", "1"))
PORTA = int(os.getenv("PORT", "5000"))

# Banco local de cada no
CAMINHO_BANCO = os.getenv(
    "DB_PATH",
    f"dados/no{ID_NO}.db"
)

persistencia = Persistencia(CAMINHO_BANCO)

# Enderecos dos nos definidos por configuracao
ENDERECOS_NOS = {
    1: os.getenv("NO1_URL", "http://localhost:5001"),
    2: os.getenv("NO2_URL", "http://localhost:5002"),
    3: os.getenv("NO3_URL", "http://localhost:5003"),
}

# Relogio logico independente para cada no
relogio = RelogioLamport()

eleicao = EleicaoBully(
    id_no=ID_NO,
    enderecos_nos=ENDERECOS_NOS,
    persistencia=persistencia
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
    dados = request.get_json(silent=True) or {}

    origem = dados.get("origem")
    mandato = dados.get("mandato")

    if (
        type(origem) is not int
        or origem not in ENDERECOS_NOS
        or type(mandato) is not int
        or mandato < 0
    ):
        return jsonify({
            "erro": "Dados invalidos"
        }), 400

    aceita = eleicao.receber_eleicao(
        origem,
        mandato
    )

    if not aceita:
        return jsonify({
            "erro": "Prioridade invalida"
        }), 400

    return jsonify({
        "no": ID_NO,
        "resposta": "OK",
        "mandato": persistencia.obter_mandato()
    })

@app.route("/coordenador", methods=["POST"])
def receber_coordenador():
    dados = request.get_json(silent=True) or {}

    id_lider = dados.get("lider")
    mandato = dados.get("mandato")

    if (
        type(id_lider) is not int
        or type(mandato) is not int
        or mandato < 0
    ):
        return jsonify({
            "erro": "Dados invalidos"
        }), 400

    if not eleicao.receber_coordenador(
        id_lider,
        mandato
    ):
        return jsonify({
            "erro": "Anuncio de lider rejeitado"
        }), 409

    return jsonify({
        "no": ID_NO,
        "lider": id_lider,
        "mandato": mandato
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

@app.route("/mandato", methods=["GET"])
def consultar_mandato():
    return jsonify({
        "no": ID_NO,
        "mandato": persistencia.obter_mandato()
    })


@app.route("/replicacao/receber", methods=["POST"])
def receber_operacao():
    dados = request.get_json(silent=True) or {}

    origem = dados.get("origem")
    operacao = dados.get("operacao")

    if (
        type(origem) is not int
        or origem not in ENDERECOS_NOS
        or origem == ID_NO
        or not isinstance(operacao, dict)
    ):
        return jsonify({
            "erro": "Mensagem de replicacao invalida"
        }), 400

    # Verificacao preliminar do lider conhecido
    lider_conhecido = eleicao.obter_estado()["lider"]

    if lider_conhecido != origem:
        return jsonify({
            "erro": "Origem nao corresponde ao lider conhecido"
        }), 409

    sucesso, mensagem = persistencia.salvar_ou_validar_operacao(
        operacao.get("id_operacao"),
        operacao.get("eleitor"),
        operacao.get("opcao"),
        operacao.get("mandato"),
        operacao.get("sequencia")
    )

    if not sucesso:
        return jsonify({
            "no": ID_NO,
            "erro": mensagem
        }), 409

    print(
        f"[Replicacao] No {ID_NO} armazenou "
        f"operacao {operacao['id_operacao']}",
        flush=True
    )

    return jsonify({
        "no": ID_NO,
        "status": "pendente",
        "id_operacao": operacao["id_operacao"]
    }), 200


@app.route("/replicacao/teste", methods=["POST"])
def testar_replicacao():
    dados = request.get_json(silent=True) or {}

    # Apenas o lider conhecido pode iniciar o teste
    estado_eleicao = eleicao.obter_estado()

    if estado_eleicao["lider"] != ID_NO:
        return jsonify({
            "erro": "Este no nao e o lider",
            "lider_conhecido": estado_eleicao["lider"]
        }), 409

    id_operacao = dados.get("id_operacao")
    eleitor = dados.get("eleitor")
    opcao = dados.get("opcao")
    sequencia = dados.get("sequencia")

    operacao = {
        "id_operacao": id_operacao,
        "eleitor": eleitor,
        "opcao": opcao,
        "mandato": persistencia.obter_mandato(),
        "sequencia": sequencia
    }

    # Armazena a operacao no lider
    sucesso, mensagem = persistencia.salvar_ou_validar_operacao(
        operacao["id_operacao"],
        operacao["eleitor"],
        operacao["opcao"],
        operacao["mandato"],
        operacao["sequencia"]
    )

    if not sucesso:
        return jsonify({
            "erro": mensagem
        }), 409

    # Envia aos outros servidores
    resultados = enviar_operacao(
        ID_NO,
        ENDERECOS_NOS,
        operacao
    )

    replicas_ok = sum(
        1 for resultado in resultados.values()
        if resultado["sucesso"]
    )

    replicacao_completa = (
        replicas_ok == len(ENDERECOS_NOS) - 1
    )

    return jsonify({
        "origem": ID_NO,
        "id_operacao": id_operacao,
        "estado": "pendente",
        "replicacao_completa": replicacao_completa,
        "replicas": resultados
    }), 200 if replicacao_completa else 503

@app.route("/operacoes", methods=["GET"])
def listar_operacoes():
    return jsonify({
        "no": ID_NO,
        "operacoes": persistencia.consultar_operacoes()
    })

@app.route("/autorizacao", methods=["GET"])
def consultar_autorizacao():
    return jsonify({
        "no": ID_NO,
        "autorizacao": persistencia.consultar_autorizacao()
    })


@app.route("/autorizacao/solicitar", methods=["POST"])
def solicitar_autorizacao():
    dados = request.get_json(silent=True) or {}

    candidato = dados.get("candidato")
    mandato = dados.get("mandato")

    if (
        type(candidato) is not int
        or candidato not in ENDERECOS_NOS
        or type(mandato) is not int
        or mandato <= 0
    ):
        return jsonify({
            "erro": "Dados de autorizacao invalidos"
        }), 400

    sucesso, mensagem = persistencia.registrar_autorizacao(
        mandato,
        candidato
    )

    estado = persistencia.consultar_autorizacao()

    print(
        f"[Autorizacao] No {ID_NO}: "
        f"proposta ({mandato}, {candidato}) - {mensagem}",
        flush=True
    )

    return jsonify({
        "no": ID_NO,
        "autorizado": sucesso,
        "mensagem": mensagem,
        "maior_proposta": estado
    }), 200 if sucesso else 409

@app.route("/autorizacao/enviar/<int:id_destino>", methods=["POST"])
def enviar_autorizacao(id_destino):
    if id_destino not in ENDERECOS_NOS or id_destino == ID_NO:
        return jsonify({
            "erro": "Destino invalido"
        }), 400

    dados = request.get_json(silent=True) or {}
    mandato = dados.get("mandato")

    if type(mandato) is not int or mandato <= 0:
        return jsonify({
            "erro": "Mandato invalido"
        }), 400

    try:
        resposta = requests.post(
            f"{ENDERECOS_NOS[id_destino]}/autorizacao/solicitar",
            json={
                "candidato": ID_NO,
                "mandato": mandato
            },
            timeout=3
        )

        return jsonify({
            "origem": ID_NO,
            "destino": id_destino,
            "codigo_http": resposta.status_code,
            "resposta": resposta.json()
        }), resposta.status_code

    except (requests.RequestException, ValueError) as erro:
        print(
            f"[Autorizacao] Falha na comunicacao: {erro}",
            flush=True
        )

        return jsonify({
            "erro": "Nao foi possivel consultar o destino",
            "destino": id_destino
        }), 503


@app.route("/autorizacao/quorum/teste", methods=["POST"])
def testar_quorum():
    dados = request.get_json(silent=True) or {}
    mandato = dados.get("mandato")

    if type(mandato) is not int or mandato <= 0:
        return jsonify({
            "erro": "Mandato invalido"
        }), 400

    # Somente o lider identificado pelo Bully inicia este teste
    estado_eleicao = eleicao.obter_estado()

    if estado_eleicao["lider"] != ID_NO:
        return jsonify({
            "erro": "Este no nao e o lider identificado",
            "lider_conhecido": estado_eleicao["lider"]
        }), 409

    # Calcula a maioria necessaria
    total_nos = len(ENDERECOS_NOS)
    maioria = total_nos // 2 + 1

    autorizacoes = 0
    respostas = {}

    # Primeiro registra a propria promessa
    sucesso_local, mensagem_local = (
        persistencia.registrar_autorizacao(
            mandato, ID_NO
        )
    )

    respostas[str(ID_NO)] = {
        "autorizado": sucesso_local,
        "mensagem": mensagem_local
    }

    if sucesso_local:
        autorizacoes += 1

    # Envia a mesma proposta aos outros nos
    for id_destino, endereco in ENDERECOS_NOS.items():

        if id_destino == ID_NO:
            continue

        try:
            resposta = requests.post(
                f"{endereco}/autorizacao/solicitar",
                json={
                    "mandato": mandato,
                    "candidato": ID_NO
                },
                timeout=3
            )

            conteudo = resposta.json()

            # Confere se a resposta corresponde
            # exatamente a proposta solicitada
            proposta = conteudo.get("maior_proposta", {})

            autorizado = (
                resposta.status_code == 200
                and conteudo.get("autorizado") is True
                and proposta.get("mandato") == mandato
                and proposta.get("candidato") == ID_NO
            )

            respostas[str(id_destino)] = {
                "autorizado": autorizado,
                "codigo_http": resposta.status_code,
                "mensagem": conteudo.get("mensagem")
            }

            if autorizado:
                autorizacoes += 1

        except (requests.RequestException, ValueError) as erro:
            respostas[str(id_destino)] = {
                "autorizado": False,
                "erro": str(erro)
            }

    quorum_obtido = autorizacoes >= maioria

    print(
        f"[Quorum] Proposta ({mandato}, {ID_NO}): "
        f"{autorizacoes}/{total_nos} autorizacoes",
        flush=True
    )

    return jsonify({
        "no": ID_NO,
        "proposta": {
            "mandato": mandato,
            "candidato": ID_NO
        },
        "total_nos": total_nos,
        "maioria_necessaria": maioria,
        "autorizacoes": autorizacoes,
        "quorum_obtido": quorum_obtido,
        "respostas": respostas
    }), 200


@app.route("/recuperacao/consultar", methods=["GET"])
def consultar_estado_distribuido():
    estado_eleicao = eleicao.obter_estado()

    # Somente o lider identificado inicia a coleta
    if estado_eleicao["lider"] != ID_NO:
        return jsonify({
            "erro": "Este no nao e o lider identificado",
            "lider_conhecido": estado_eleicao["lider"]
        }), 409

    resultado = coletar_estados(
        ID_NO,
        ENDERECOS_NOS,
        persistencia
    )

    maioria = len(ENDERECOS_NOS) // 2 + 1

    resultado["maioria_necessaria"] = maioria
    resultado["maioria_consultada"] = (
        resultado["nos_consultados"] >= maioria
    )

    print(
        f"[Recuperacao] No {ID_NO}: "
        f"{resultado['nos_consultados']} "
        f"de {resultado['total_nos']} estados coletados",
        flush=True
    )

    return jsonify(resultado)


@app.route("/recuperacao/comparar", methods=["GET"])
def comparar_operacoes_distribuidas():
    estado_eleicao = eleicao.obter_estado()

    if estado_eleicao["lider"] != ID_NO:
        return jsonify({
            "erro": "Este no nao e o lider identificado",
            "lider_conhecido": estado_eleicao["lider"]
        }), 409

    coleta = coletar_estados(
        ID_NO,
        ENDERECOS_NOS,
        persistencia
    )

    comparacao = comparar_estados(coleta)

    maioria = len(ENDERECOS_NOS) // 2 + 1

    return jsonify({
        "no": ID_NO,
        "nos_consultados": coleta["nos_consultados"],
        "maioria_consultada": (
            coleta["nos_consultados"] >= maioria
        ),
        "comparacao": comparacao
    })

@app.route("/resultados", methods=["GET"])
def consultar_resultados():
    resultados = persistencia.consultar_votos()

    return jsonify({
        "no": ID_NO,
        "total_votos": resultados["total_votos"],
        "resultados": resultados["resultados"]
    })



def verificar_maioria_ativa():
    nos_ativos = [ID_NO]

    for id_no, endereco in ENDERECOS_NOS.items():
        if id_no == ID_NO:
            continue

        try:
            resposta = requests.get(
                f"{endereco}/status",
                timeout=2
            )

            if resposta.status_code == 200:
                dados = resposta.json()

                if dados.get("no") == id_no:
                    nos_ativos.append(id_no)

        except (requests.RequestException, ValueError):
            pass

    total_nos = len(ENDERECOS_NOS)
    maioria = total_nos // 2 + 1

    return {
        "nos_ativos": sorted(nos_ativos),
        "maioria_necessaria": maioria,
        "quorum_disponivel": len(nos_ativos) >= maioria
    }


@app.route("/votar", methods=["POST"])
def receber_solicitacao_voto():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "erro": "Envie um objeto JSON valido"
        }), 400

    eleitor = dados.get("eleitor")
    opcao = dados.get("opcao")

    if not isinstance(eleitor, str) or not eleitor.strip():
        return jsonify({
            "erro": "Identificador do eleitor invalido"
        }), 400

    if opcao not in ("python", "java", "javascript"):
        return jsonify({
            "erro": "Opcao de voto invalida"
        }), 400

    eleitor = eleitor.strip()

    # Identifica o lider pelo algoritmo Bully
    estado_eleicao = eleicao.obter_estado()
    lider = estado_eleicao["lider"]

    if lider not in ENDERECOS_NOS:
        return jsonify({
            "erro": "Lider indisponivel"
        }), 503

    # Encaminha ao lider quando necessario
    if lider != ID_NO:
        try:
            resposta = requests.post(
                f"{ENDERECOS_NOS[lider]}/votar",
                json={
                    "eleitor": eleitor,
                    "opcao": opcao
                },
                timeout=20
            )

            return (
                resposta.content,
                resposta.status_code,
                {
                    "Content-Type": resposta.headers.get(
                        "Content-Type", "application/json"
                    )
                }
            )

        except requests.RequestException:
            return jsonify({
                "erro": "Nao foi possivel contactar o lider",
                "lider_conhecido": lider
            }), 503

    # Verifica se existe maioria de servidores ativos
    quorum = verificar_maioria_ativa()
    nos_ativos = quorum["nos_ativos"]
    maioria = quorum["maioria_necessaria"]

    if not quorum["quorum_disponivel"]:
        return jsonify({
            "status": "sem_quorum",
            "mensagem": "Servidores insuficientes para votar",
            "nos_ativos": nos_ativos,
            "voto_confirmado": False
        }), 503

    # Verificacao preliminar:
    # os nos ativos precisam reconhecer este lider
    for id_no in nos_ativos:
        if id_no == ID_NO:
            continue

        try:
            resposta = requests.get(
                f"{ENDERECOS_NOS[id_no]}/lider",
                timeout=3
            )

            resposta.raise_for_status()
            estado_remoto = resposta.json()

            if estado_remoto.get("lider") != ID_NO:
                return jsonify({
                    "status": "lideranca_instavel",
                    "mensagem": "Os servidores nao concordam sobre o lider",
                    "voto_confirmado": False
                }), 503

        except (requests.RequestException, ValueError):
            return jsonify({
                "status": "lideranca_instavel",
                "mensagem": "Falha ao verificar a lideranca",
                "voto_confirmado": False
            }), 503

    # Cria a operacao pendente no lider
    mandato = persistencia.obter_mandato()

    sucesso, mensagem, operacao = (
        persistencia.criar_operacao_voto(
            eleitor,
            opcao,
            mandato
        )
    )

    if not sucesso:
        return jsonify({
            "erro": mensagem,
            "lider": ID_NO
        }), 409

    # Replica a operacao
    resultados_replicacao = enviar_operacao(
        ID_NO,
        ENDERECOS_NOS,
        operacao
    )

    # O lider ja possui uma copia local
    total_copias = 1
    replicas_aceitas = []

    for id_no, resultado in resultados_replicacao.items():
        if resultado["sucesso"]:
            total_copias += 1
            replicas_aceitas.append(int(id_no))

    # Exige pelo menos duas copias, incluindo o lider
    if total_copias < maioria:
        return jsonify({
            "status": "pendente",
            "mensagem": "Nao foi possivel obter maioria de replicas",
            "id_operacao": operacao["id_operacao"],
            "copias_armazenadas": total_copias,
            "voto_confirmado": False
        }), 503

    # Solicita confirmacao somente as replicas
    # que armazenaram a operacao
    confirmacoes = {}
    total_confirmacoes = 0

    for id_no in replicas_aceitas:
        endereco = ENDERECOS_NOS[id_no]

        try:
            resposta = requests.post(
                f"{endereco}/replicacao/confirmar",
                json={
                    "origem": ID_NO,
                    "id_operacao": operacao["id_operacao"],
                    "mandato": operacao["mandato"]
                },
                timeout=3
            )

            dados_resposta = resposta.json()

            confirmado = (
                resposta.status_code == 200
                and dados_resposta.get("confirmado") is True
            )

            confirmacoes[str(id_no)] = {
                "confirmado": confirmado,
                "codigo_http": resposta.status_code
            }

            if confirmado:
                total_confirmacoes += 1

        except (requests.RequestException, ValueError) as erro:
            confirmacoes[str(id_no)] = {
                "confirmado": False,
                "erro": str(erro)
            }

    # O lider so confirma localmente quando pelo menos
    # outro servidor respondeu positivamente
    if total_confirmacoes + 1 < maioria:
        return jsonify({
            "status": "confirmacao_parcial",
            "mensagem": "Nao foi possivel obter maioria na confirmacao",
            "id_operacao": operacao["id_operacao"],
            "voto_confirmado": False,
            "confirmacoes": confirmacoes
        }), 503

    # Confirma no proprio banco do lider
    sucesso_local, mensagem_local = (
        persistencia.confirmar_operacao_local(
            operacao["id_operacao"]
        )
    )

    if not sucesso_local:
        return jsonify({
            "status": "confirmacao_parcial",
            "erro": mensagem_local,
            "id_operacao": operacao["id_operacao"],
            "voto_confirmado": False,
            "confirmacoes": confirmacoes
        }), 503

    total_confirmacoes += 1

    print(
        f"[Votacao] Operacao {operacao['id_operacao']} "
        f"confirmada em {total_confirmacoes}/{len(ENDERECOS_NOS)} nos",
        flush=True
    )

    return jsonify({
        "status": "confirmado",
        "mensagem": "Voto confirmado no teste de maioria",
        "lider": ID_NO,
        "id_operacao": operacao["id_operacao"],
        "eleitor": eleitor,
        "opcao": opcao,
        "nos_confirmados": total_confirmacoes,
        "maioria_necessaria": maioria,
        "voto_confirmado": True,
        "confirmacoes": confirmacoes
    }), 200

@app.route("/replicacao/confirmar", methods=["POST"])
def receber_confirmacao():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "erro": "Dados invalidos"
        }), 400

    origem = dados.get("origem")
    id_operacao = dados.get("id_operacao")
    mandato = dados.get("mandato")

    if (
        type(origem) is not int
        or origem not in ENDERECOS_NOS
        or origem == ID_NO
        or not isinstance(id_operacao, str)
        or not id_operacao.strip()
        or type(mandato) is not int
        or mandato < 0
    ):
        return jsonify({
            "erro": "Solicitacao de confirmacao invalida"
        }), 400

    # Aceita apenas comandos do lider conhecido
    estado_eleicao = eleicao.obter_estado()

    if estado_eleicao["lider"] != origem:
        return jsonify({
            "erro": "Origem nao corresponde ao lider conhecido"
        }), 409

    # Confere se a operacao existe com o mandato informado
    operacoes = persistencia.consultar_operacoes()

    operacao = next(
        (
            item for item in operacoes
            if item["id_operacao"] == id_operacao
        ),
        None
    )

    if operacao is None:
        return jsonify({
            "erro": "Operacao nao encontrada"
        }), 404

    if operacao["mandato"] != mandato:
        return jsonify({
            "erro": "Mandato diferente do registro armazenado"
        }), 409

    # Executa a confirmacao local em uma transacao SQLite
    sucesso, mensagem = persistencia.confirmar_operacao_local(
        id_operacao
    )

    print(
        f"[Confirmacao] No {ID_NO}: "
        f"{id_operacao} - {mensagem}",
        flush=True
    )

    return jsonify({
        "no": ID_NO,
        "id_operacao": id_operacao,
        "confirmado": sucesso,
        "mensagem": mensagem
    }), 200 if sucesso else 409

@app.route("/enquete", methods=["GET"])
def pagina_enquete():
    return render_template("enquete.html")


@app.route(
    "/recuperacao/sincronizar-pendente/<id_operacao>",
    methods=["POST"]
)
def sincronizar_operacao_pendente(id_operacao):

    # Nesta etapa, a sincronizacao sera iniciada
    # somente pelo lider identificado pelo Bully.
    estado_eleicao = eleicao.obter_estado()

    if estado_eleicao["lider"] != ID_NO:
        return jsonify({
            "erro": "Este no nao e o lider"
        }), 409

    # Consulta os outros servidores
    copias = []

    for id_no, endereco in ENDERECOS_NOS.items():
        if id_no == ID_NO:
            continue

        try:
            resposta = requests.get(
                f"{endereco}/operacoes",
                timeout=3
            )

            resposta.raise_for_status()
            dados = resposta.json()

            if dados.get("no") != id_no:
                return jsonify({
                    "erro": "Resposta de servidor inesperado"
                }), 409

            operacao = next(
                (
                    item for item in dados["operacoes"]
                    if item["id_operacao"] == id_operacao
                ),
                None
            )

            if operacao is not None:
                copias.append(operacao)

        except (requests.RequestException, ValueError, KeyError):
            return jsonify({
                "erro": "Falha ao consultar os servidores"
            }), 503

    # Exige duas copias para este teste de recuperacao
    if len(copias) != 2:
        return jsonify({
            "erro": "Nao foram encontradas duas copias"
        }), 409

    primeira, segunda = copias

    # As duas copias precisam ser identicas
    if primeira != segunda:
        return jsonify({
            "erro": "As copias apresentam divergencias"
        }), 409

    if primeira["estado"] != "pendente":
        return jsonify({
            "erro": "Recuperacao aceita apenas operacoes pendentes"
        }), 409

    # Impede conflito com registros ja existentes
    operacoes_locais = persistencia.consultar_operacoes()

    for existente in operacoes_locais:
        mesmo_id = (
            existente["id_operacao"] == id_operacao
        )

        mesma_posicao = (
            existente["mandato"] == primeira["mandato"]
            and existente["sequencia"] == primeira["sequencia"]
        )

        mesmo_eleitor = (
            existente["eleitor"] == primeira["eleitor"]
        )

        if (mesma_posicao or mesmo_eleitor) and not mesmo_id:
            return jsonify({
                "erro": "Conflito com operacao local existente"
            }), 409

    sucesso, mensagem = (
        persistencia.salvar_ou_validar_operacao(
            primeira["id_operacao"],
            primeira["eleitor"],
            primeira["opcao"],
            primeira["mandato"],
            primeira["sequencia"]
        )
    )

    if not sucesso:
        return jsonify({
            "erro": mensagem
        }), 409

    return jsonify({
        "no": ID_NO,
        "id_operacao": id_operacao,
        "status": "pendente",
        "mensagem": "Operacao sincronizada com sucesso"
    }), 200



@app.route(
    "/recuperacao/finalizar/<id_operacao>",
    methods=["POST"]
)
def finalizar_operacao_recuperada(id_operacao):

    # Apenas o lider conhecido inicia a recuperacao
    estado_eleicao = eleicao.obter_estado()

    if estado_eleicao["lider"] != ID_NO:
        return jsonify({
            "erro": "Este no nao e o lider"
        }), 409

    # Consulta as operacoes dos tres servidores
    estados = {}

    for id_no, endereco in ENDERECOS_NOS.items():
        if id_no == ID_NO:
            operacoes = persistencia.consultar_operacoes()
        else:
            try:
                resposta = requests.get(
                    f"{endereco}/operacoes",
                    timeout=3
                )
                resposta.raise_for_status()
                dados = resposta.json()

                if (
                    dados.get("no") != id_no
                    or not isinstance(dados.get("operacoes"), list)
                ):
                    return jsonify({
                        "erro": "Resposta de servidor invalida"
                    }), 409

                operacoes = dados["operacoes"]

            except (requests.RequestException, ValueError):
                return jsonify({
                    "erro": "Todos os nos devem estar disponiveis"
                }), 503

        estados[id_no] = operacoes

    # Localiza a operacao em cada servidor
    copias = {}

    for id_no, operacoes in estados.items():
        encontrada = next(
            (
                op for op in operacoes
                if op["id_operacao"] == id_operacao
            ),
            None
        )

        if encontrada is None:
            return jsonify({
                "erro": "Operacao ausente em um dos nos",
                "no": id_no
            }), 409

        copias[id_no] = encontrada

    # Confere os dados da operacao
    campos = (
        "id_operacao",
        "eleitor",
        "opcao",
        "mandato",
        "sequencia"
    )

    referencia = tuple(
        copias[ID_NO][campo] for campo in campos
    )

    for copia in copias.values():
        dados_copia = tuple(
            copia[campo] for campo in campos
        )

        if dados_copia != referencia:
            return jsonify({
                "erro": "Operacoes divergentes entre os nos"
            }), 409

        if copia["estado"] not in (
            "pendente", "confirmada"
        ):
            return jsonify({
                "erro": "Estado de operacao invalido"
            }), 409

    # Evita confirmar operacoes concorrentes
    eleitor = copias[ID_NO]["eleitor"]
    mandato = copias[ID_NO]["mandato"]
    sequencia = copias[ID_NO]["sequencia"]

    for operacoes in estados.values():
        for op in operacoes:
            if op["id_operacao"] == id_operacao:
                continue

            if op["eleitor"] == eleitor:
                return jsonify({
                    "erro": "Outra operacao existe para o eleitor"
                }), 409

            if (
                op["mandato"] == mandato
                and op["sequencia"] == sequencia
            ):
                return jsonify({
                    "erro": "Conflito na posicao da operacao"
                }), 409

    # Solicita confirmacao aos outros nos
    confirmacoes = {}

    for id_no, endereco in ENDERECOS_NOS.items():
        if id_no == ID_NO:
            continue

        try:
            resposta = requests.post(
                f"{endereco}/replicacao/confirmar",
                json={
                    "origem": ID_NO,
                    "id_operacao": id_operacao,
                    "mandato": mandato
                },
                timeout=3
            )

            dados = resposta.json()

            if (
                resposta.status_code != 200
                or dados.get("confirmado") is not True
            ):
                return jsonify({
                    "status": "confirmacao_parcial",
                    "erro": "Falha ao confirmar em uma replica",
                    "no": id_no,
                    "confirmacoes": confirmacoes
                }), 503

            confirmacoes[str(id_no)] = True

        except (requests.RequestException, ValueError):
            return jsonify({
                "status": "confirmacao_parcial",
                "erro": "Falha na comunicacao",
                "no": id_no,
                "confirmacoes": confirmacoes
            }), 503

    # Confirma no banco local do lider
    sucesso, mensagem = (
        persistencia.confirmar_operacao_local(
            id_operacao
        )
    )

    if not sucesso:
        return jsonify({
            "status": "confirmacao_parcial",
            "erro": mensagem,
            "confirmacoes": confirmacoes
        }), 503

    return jsonify({
        "status": "confirmado",
        "mensagem": "Operacao finalizada nos tres nos",
        "id_operacao": id_operacao,
        "lider": ID_NO,
        "voto_confirmado": True
    }), 200


@app.route("/votacao/quorum", methods=["GET"])
def verificar_quorum_votacao():
    nos_ativos = [ID_NO]
    nos_indisponiveis = []

    # Consulta os demais servidores
    for id_no, endereco in ENDERECOS_NOS.items():
        if id_no == ID_NO:
            continue

        try:
            resposta = requests.get(
                f"{endereco}/status",
                timeout=2
            )

            if resposta.status_code == 200:
                dados = resposta.json()

                # Confere se o servidor respondeu
                # com o identificador esperado
                if dados.get("no") == id_no:
                    nos_ativos.append(id_no)
                else:
                    nos_indisponiveis.append(id_no)
            else:
                nos_indisponiveis.append(id_no)

        except (requests.RequestException, ValueError):
            nos_indisponiveis.append(id_no)

    total_nos = len(ENDERECOS_NOS)
    maioria_necessaria = total_nos // 2 + 1

    quorum_disponivel = (
        len(nos_ativos) >= maioria_necessaria
    )

    estado_eleicao = eleicao.obter_estado()

    return jsonify({
        "no": ID_NO,
        "lider_conhecido": estado_eleicao["lider"],
        "total_nos": total_nos,
        "maioria_necessaria": maioria_necessaria,
        "nos_ativos": sorted(nos_ativos),
        "nos_indisponiveis": sorted(nos_indisponiveis),
        "quorum_disponivel": quorum_disponivel
    })


@app.route(
    "/recuperacao/sincronizar-confirmada/<id_operacao>",
    methods=["POST"]
)
def sincronizar_operacao_confirmada(id_operacao):

    # Consulta as operacoes dos outros dois servidores
    copias = []

    for id_no, endereco in ENDERECOS_NOS.items():
        if id_no == ID_NO:
            continue

        try:
            resposta = requests.get(
                f"{endereco}/operacoes",
                timeout=3
            )

            resposta.raise_for_status()
            dados = resposta.json()

            if (
                dados.get("no") != id_no
                or not isinstance(dados.get("operacoes"), list)
            ):
                return jsonify({
                    "erro": "Resposta de servidor invalida"
                }), 409

            operacao = next(
                (
                    op for op in dados["operacoes"]
                    if op.get("id_operacao") == id_operacao
                ),
                None
            )

            if operacao is None:
                return jsonify({
                    "erro": "Operacao ausente em uma replica",
                    "no": id_no
                }), 409

            copias.append(operacao)

        except (
            requests.RequestException,
            ValueError,
            KeyError
        ):
            return jsonify({
                "erro": "Falha ao consultar as replicas"
            }), 503

    # Exige duas copias confirmadas
    if len(copias) != 2:
        return jsonify({
            "erro": "Duas copias sao necessarias"
        }), 409

    primeira, segunda = copias

    if primeira != segunda:
        return jsonify({
            "erro": "As replicas possuem dados diferentes"
        }), 409

    if primeira["estado"] != "confirmada":
        return jsonify({
            "erro": "A operacao ainda nao foi confirmada"
        }), 409

    # Verifica conflitos com operacoes locais
    operacoes_locais = persistencia.consultar_operacoes()

    for existente in operacoes_locais:
        if existente["id_operacao"] == id_operacao:

            campos = (
                "eleitor",
                "opcao",
                "mandato",
                "sequencia"
            )

            if any(
                existente[campo] != primeira[campo]
                for campo in campos
            ):
                return jsonify({
                    "erro": "Conflito com operacao local"
                }), 409

            continue

        if existente["eleitor"] == primeira["eleitor"]:
            return jsonify({
                "erro": "Outra operacao existe para o eleitor"
            }), 409

        if (
            existente["mandato"] == primeira["mandato"]
            and existente["sequencia"] == primeira["sequencia"]
        ):
            return jsonify({
                "erro": "Conflito na posicao da operacao"
            }), 409

    # Verifica se ja existe voto local para o eleitor
    with persistencia.lock:
        with persistencia.conectar() as conexao:
            voto_existente = conexao.execute("""
                SELECT opcao
                FROM votos
                WHERE eleitor = ?
            """, (primeira["eleitor"],)).fetchone()

    if voto_existente is not None:
        operacao_local = next(
            (
                op for op in operacoes_locais
                if op["id_operacao"] == id_operacao
            ),
            None
        )

        if (
            operacao_local is None
            or operacao_local["estado"] != "confirmada"
            or voto_existente[0] != primeira["opcao"]
        ):
            return jsonify({
                "erro": "Conflito com voto local existente"
            }), 409

    # Armazena a operacao, se ainda nao existir
    sucesso, mensagem = (
        persistencia.salvar_ou_validar_operacao(
            primeira["id_operacao"],
            primeira["eleitor"],
            primeira["opcao"],
            primeira["mandato"],
            primeira["sequencia"]
        )
    )

    if not sucesso:
        return jsonify({
            "erro": mensagem
        }), 409

    # Confirma a operacao localmente
    sucesso, mensagem = (
        persistencia.confirmar_operacao_local(
            id_operacao
        )
    )

    if not sucesso:
        return jsonify({
            "erro": mensagem
        }), 409

    print(
        f"[Recuperacao] No {ID_NO} recuperou "
        f"voto confirmado {id_operacao}",
        flush=True
    )

    return jsonify({
        "no": ID_NO,
        "id_operacao": id_operacao,
        "status": "confirmada",
        "mensagem": "Voto confirmado recuperado com sucesso"
    }), 200


@app.route(
    "/recuperacao/sincronizar-confirmadas",
    methods=["POST"]
)
def sincronizar_operacoes_confirmadas():

    # Coleta os estados dos tres servidores
    coleta = coletar_estados(
        ID_NO,
        ENDERECOS_NOS,
        persistencia
    )

    # Para este procedimento controlado,
    # precisamos consultar os tres nos
    if coleta["nos_consultados"] != len(ENDERECOS_NOS):
        return jsonify({
            "erro": "Todos os nos devem estar disponiveis",
            "detalhes": coleta["erros"]
        }), 503

    # Identifica os dois outros servidores
    outros_nos = [
        str(id_no)
        for id_no in ENDERECOS_NOS
        if id_no != ID_NO
    ]

    primeiro_no, segundo_no = outros_nos

    operacoes_primeiro = {
        op["id_operacao"]: op
        for op in coleta["estados"][primeiro_no]
    }

    operacoes_segundo = {
        op["id_operacao"]: op
        for op in coleta["estados"][segundo_no]
    }

    operacoes_locais = {
        op["id_operacao"]: op
        for op in coleta["estados"][str(ID_NO)]
    }

    # Seleciona operacoes confirmadas e identicas
    # que ainda nao estao confirmadas localmente
    candidatos = []

    for id_operacao, primeira in operacoes_primeiro.items():

        segunda = operacoes_segundo.get(id_operacao)

        if segunda is None:
            continue

        if primeira != segunda:
            continue

        if primeira["estado"] != "confirmada":
            continue

        local = operacoes_locais.get(id_operacao)

        if local is not None and local["estado"] == "confirmada":
            continue

        candidatos.append(primeira)

    # Recupera na ordem original das operacoes
    candidatos.sort(
        key=lambda op: (
            op["mandato"],
            op["sequencia"],
            op["id_operacao"]
        )
    )

    recuperadas = []
    falhas = []

    # Reutiliza a rota individual ja testada
    for operacao in candidatos:
        id_operacao = operacao["id_operacao"]

        resposta, codigo = sincronizar_operacao_confirmada(
            id_operacao
        )

        dados = resposta.get_json()

        if codigo == 200:
            recuperadas.append(id_operacao)
        else:
            falhas.append({
                "id_operacao": id_operacao,
                "codigo_http": codigo,
                "detalhes": dados
            })

    print(
        f"[Recuperacao] No {ID_NO}: "
        f"{len(recuperadas)} operacoes recuperadas, "
        f"{len(falhas)} falhas",
        flush=True
    )

    return jsonify({
        "no": ID_NO,
        "operacoes_identificadas": len(candidatos),
        "operacoes_recuperadas": len(recuperadas),
        "recuperadas": recuperadas,
        "falhas": falhas
    }), 200 if not falhas else 409


def monitorar_recuperacao_automatica():
    while True:
        # Intervalo entre as verificacoes
        time.sleep(10)

        try:
            # Verifica se todos os servidores estao ativos
            quorum = verificar_maioria_ativa()

            if len(quorum["nos_ativos"]) != len(ENDERECOS_NOS):
                continue

            # Cada servidor recupera seu proprio banco
            resposta = requests.post(
                f"http://127.0.0.1:{PORTA}/recuperacao/sincronizar-confirmadas",
                timeout=30
            )

            if resposta.status_code != 200:
                print(
                    f"[Recuperacao automatica] No {ID_NO}: "
                    f"HTTP {resposta.status_code}",
                    flush=True
                )
                continue

            dados = resposta.json()

            quantidade = dados.get(
                "operacoes_recuperadas", 0
            )

            falhas = dados.get("falhas", [])

            if quantidade > 0:
                print(
                    f"[Recuperacao automatica] No {ID_NO}: "
                    f"{quantidade} voto(s) recuperado(s)",
                    flush=True
                )

            if falhas:
                print(
                    f"[Recuperacao automatica] No {ID_NO}: "
                    f"{len(falhas)} operacao(oes) "
                    "precisam de verificacao",
                    flush=True
                )

        except (requests.RequestException, ValueError) as erro:
            print(
                f"[Recuperacao automatica] No {ID_NO}: "
                f"Erro: {erro}",
                flush=True
            )



if __name__ == "__main__":
    monitor.iniciar()

    # Aguarda os servidores iniciarem antes da eleicao
    threading.Timer(
        5,
        eleicao.iniciar_em_thread
    ).start()

    monitor_recuperacao = threading.Thread(
        target=monitorar_recuperacao_automatica,
        daemon=True
    )

    monitor_recuperacao.start()

    app.run(
        host="0.0.0.0",
        port=PORTA,
        debug=False,
        use_reloader=False
    )
