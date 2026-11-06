
import threading

import requests


class EleicaoBully:
    def __init__(self, id_no, enderecos_nos):
        self.id_no = id_no
        self.enderecos_nos = enderecos_nos

        self.lider_atual = None
        self.eleicao_em_andamento = False
        self.lock = threading.Lock()

    def obter_estado(self):
        with self.lock:
            return {
                "no": self.id_no,
                "lider": self.lider_atual,
                "eleicao_em_andamento": self.eleicao_em_andamento
            }

    def iniciar_em_thread(self):
        with self.lock:
            if self.eleicao_em_andamento:
                return False

            self.eleicao_em_andamento = True
            self.lider_atual = None

        thread = threading.Thread(
            target=self.iniciar_eleicao,
            daemon=True
        )
        thread.start()
        return True

    def iniciar_eleicao(self):
        print(
            f"[Eleicao] No {self.id_no} iniciou uma eleicao",
            flush=True
        )

        respondeu_no_superior = False

        for id_no, endereco in self.enderecos_nos.items():
            if id_no <= self.id_no:
                continue

            try:
                resposta = requests.post(
                    f"{endereco}/eleicao",
                    json={"origem": self.id_no},
                    timeout=2
                )

                if resposta.status_code == 200:
                    respondeu_no_superior = True
                    print(
                        f"[Eleicao] No {id_no} respondeu",
                        flush=True
                    )

            except requests.RequestException:
                print(
                    f"[Eleicao] No {id_no} indisponivel",
                    flush=True
                )

        if not respondeu_no_superior:
            self.anunciar_lider()
        else:
            print(
                f"[Eleicao] No {self.id_no} aguarda coordenador",
                flush=True
            )

        with self.lock:
            self.eleicao_em_andamento = False

    def receber_eleicao(self, origem):
        if origem >= self.id_no:
            return False

        self.iniciar_em_thread()
        return True

    def anunciar_lider(self):
        with self.lock:
            self.lider_atual = self.id_no

        print(
            f"[Eleicao] No {self.id_no} assumiu a lideranca",
            flush=True
        )

        for id_no, endereco in self.enderecos_nos.items():
            if id_no == self.id_no:
                continue

            try:
                requests.post(
                    f"{endereco}/coordenador",
                    json={"lider": self.id_no},
                    timeout=2
                )
            except requests.RequestException:
                print(
                    f"[Eleicao] Nao foi possivel avisar o No {id_no}",
                    flush=True
                )

    def receber_coordenador(self, id_lider):
        if id_lider not in self.enderecos_nos:
            return False

        with self.lock:
            self.lider_atual = id_lider

        print(
            f"[Eleicao] Lider atual: No {id_lider}",
            flush=True
        )
        return True
