
import requests


def coletar_estados(id_origem, enderecos_nos, persistencia):
    estados = {}
    erros = {}

    # Consulta o banco local
    estados[str(id_origem)] = persistencia.consultar_operacoes()

    # Consulta os demais servidores
    for id_no, endereco in enderecos_nos.items():
        if id_no == id_origem:
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
                raise ValueError("Resposta de estado invalida")

            estados[str(id_no)] = dados["operacoes"]

        except (requests.RequestException, ValueError) as erro:
            erros[str(id_no)] = str(erro)

    return {
        "estados": estados,
        "erros": erros,
        "nos_consultados": len(estados),
        "total_nos": len(enderecos_nos)
    }


def comparar_estados(resultado_coleta):
    estados = resultado_coleta["estados"]
    nos_disponiveis = set(estados.keys())

    operacoes_por_id = {}
    posicoes = {}

    # Organiza as operacoes encontradas
    for id_no, operacoes in estados.items():
        for operacao in operacoes:
            id_operacao = operacao["id_operacao"]

            operacoes_por_id.setdefault(
                id_operacao, {}
            )[id_no] = operacao

            posicao = (
                operacao["mandato"],
                operacao["sequencia"]
            )

            posicoes.setdefault(
                posicao, set()
            ).add(id_operacao)

    ausentes = []
    conflitos = []
    estados_diferentes = []

    # Procura operacoes ausentes e divergentes
    for id_operacao, registros in operacoes_por_id.items():

        presentes = set(registros.keys())
        faltantes = nos_disponiveis - presentes

        if faltantes:
            ausentes.append({
                "id_operacao": id_operacao,
                "presentes_em": sorted(presentes),
                "ausentes_em": sorted(faltantes)
            })

        # Compara os dados da mesma operacao
        dados = {
            (
                registro["eleitor"],
                registro["opcao"],
                registro["mandato"],
                registro["sequencia"]
            )
            for registro in registros.values()
        }

        if len(dados) > 1:
            conflitos.append({
                "tipo": "dados_divergentes",
                "id_operacao": id_operacao,
                "registros": registros
            })

        # Compara o estado pendente/confirmada
        situacoes = {
            registro["estado"]
            for registro in registros.values()
        }

        if len(situacoes) > 1:
            estados_diferentes.append({
                "id_operacao": id_operacao,
                "estados": {
                    id_no: registro["estado"]
                    for id_no, registro in registros.items()
                }
            })

    # Procura IDs diferentes na mesma posicao
    for posicao, identificadores in posicoes.items():
        if len(identificadores) > 1:
            conflitos.append({
                "tipo": "conflito_de_posicao",
                "mandato": posicao[0],
                "sequencia": posicao[1],
                "operacoes": sorted(identificadores)
            })

    return {
        "total_operacoes_identificadas": len(
            operacoes_por_id
        ),
        "operacoes_ausentes": ausentes,
        "conflitos": conflitos,
        "estados_diferentes": estados_diferentes,
        "nos_indisponiveis": sorted(
            resultado_coleta["erros"].keys()
        )
    }
