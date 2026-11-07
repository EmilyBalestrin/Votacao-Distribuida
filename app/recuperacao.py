
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
