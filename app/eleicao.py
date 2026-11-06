
import threading

import requests


class EleicaoBully:
    def __init__(self, id_no, enderecos_nos):
        self.id_no = id_no
        self.enderecos_nos = enderecos_nos

        self.lider_atual = None
        self.eleicao_em_andamento = False
        self.lock = threading.Lock()

        # Controle do tempo de espera da eleicao
        self.tempo_espera = 5
        self.temporizador = None
        self.numero_eleicao = 0

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
            self.numero_eleicao += 1
            numero = self.numero_eleicao

            if self.temporizador is not None:
                self.temporizador.cancel()
                self.temporizador = None

        thread = threading.Thread(
            target=self.iniciar_eleicao,
            args=(numero,),
            daemon=True
        )
        thread.start()
        return True

    def iniciar_eleicao(self, numero):
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

        with self.lock:
            # Ignora resultados de uma eleicao antiga
            if numero != self.numero_eleicao:
                return

            # Um coordenador ja foi anunciado
            if not self.eleicao_em_andamento:
                return

        if respondeu_no_superior:
            print(
                f"[Eleicao] No {self.id_no} aguarda coordenador",
                flush=True
            )

            with self.lock:
                if (
                    numero != self.numero_eleicao
                    or not self.eleicao_em_andamento
                ):
                    return

                self.temporizador = threading.Timer(
                    self.tempo_espera,
                    self.verificar_timeout,
                    args=(numero,)
                )
                self.temporizador.daemon = True
                self.temporizador.start()
        else:
            self.anunciar_lider()

    def verificar_timeout(self, numero):
        with self.lock:
            if numero != self.numero_eleicao:
                return

            if not self.eleicao_em_andamento:
                return

            if self.lider_atual is not None:
                return

            self.eleicao_em_andamento = False
            self.temporizador = None

        print(
            f"[Eleicao] Timeout no No {self.id_no}. "
            "Reiniciando eleicao.",
            flush=True
        )

        self.iniciar_em_thread()

    def receber_eleicao(self, origem):
        if origem >= self.id_no:
            return False

        self.iniciar_em_thread()
        return True

    def anunciar_lider(self):
        with self.lock:
            if not self.eleicao_em_andamento:
                return

            self.lider_atual = self.id_no
            self.eleicao_em_andamento = False

            if self.temporizador is not None:
                self.temporizador.cancel()
                self.temporizador = None

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
            self.eleicao_em_andamento = False

            if self.temporizador is not None:
                self.temporizador.cancel()
                self.temporizador = None

        print(
            f"[Eleicao] Lider atual: No {id_lider}",
            flush=True
        )

        return True
