
import requests


def enviar_operacao(
    id_origem,
    enderecos_nos,
    operacao,
    relogio=None
):
    resultados = {}

    for id_no, endereco in enderecos_nos.items():

        if id_no == id_origem:
            continue

        # Registra um evento de envio no relogio
        timestamp_lamport = None

        if relogio is not None:
            relogio.enviar_mensagem()
            timestamp_lamport = relogio.obter_valor()

        try:
            resposta = requests.post(
                f"{endereco}/replicacao/receber",
                json={
                    "origem": id_origem,
                    "operacao": operacao,
                    "timestamp_lamport": timestamp_lamport
                },
                timeout=3
            )

            resultados[str(id_no)] = {
                "sucesso": resposta.status_code == 200,
                "codigo_http": resposta.status_code
            }

            print(
                f"[Replicacao] No {id_no}: "
                f"HTTP {resposta.status_code} "
                f"Lamport={timestamp_lamport}",
                flush=True
            )

        except requests.RequestException as erro:
            resultados[str(id_no)] = {
                "sucesso": False,
                "erro": str(erro)
            }

            print(
                f"[Replicacao] Falha ao comunicar "
                f"com No {id_no}: {erro}",
                flush=True
            )

    return resultados
