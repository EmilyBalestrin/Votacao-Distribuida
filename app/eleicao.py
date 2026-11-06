
import threading

import requests


class EleicaoBully:
    def __init__(self, id_no, enderecos_nos, persistencia):
        self.id_no = id_no
        self.enderecos_nos = enderecos_nos
        self.persistencia = persistencia

        self.lider_atual = None
        self.mandato_lider = None
        self.eleicao_em_andamento = False

        self.tempo_espera = 5
        self.temporizador = None
        self.numero_eleicao = 0

        self.lock = threading.RLock()

    def obter_estado(self):
        with self.lock:
            return {
                "no": self.id_no,
                "lider": self.lider_atual,
                "mandato": self.persistencia.obter_mandato(),
                "mandato_lider": self.mandato_lider,
                "eleicao_em_andamento": self.eleicao_em_andamento
            }

    def iniciar_em_thread(self):
        with self.lock:
            if self.eleicao_em_andamento:
                return False

            self.eleicao_em_andamento = True
            self.lider_atual = None
            self.mandato_lider = None
            self.numero_eleicao += 1

            numero = self.numero_eleicao

            mandato = self.persistencia.obter_mandato() + 1
            self.persistencia.atualizar_mandato(mandato)

            if self.temporizador is not None:
                self.temporizador.cancel()
                self.temporizador = None

        thread = threading.Thread(
            target=self.iniciar_eleicao,
            args=(numero, mandato),
            daemon=True
        )
        thread.start()

        return True

    def iniciar_eleicao(self, numero, mandato):
        print(
            f"[Eleicao] No {self.id_no} iniciou "
            f"eleicao no mandato {mandato}",
            flush=True
        )

        respondeu_superior = False

        for id_no, endereco in self.enderecos_nos.items():
            if id_no <= self.id_no:
                continue

            try:
                resposta = requests.post(
                    f"{endereco}/eleicao",
                    json={
                        "origem": self.id_no,
                        "mandato": mandato
                    },
                    timeout=2
                )

                if resposta.status_code == 200:
                    respondeu_superior = True

                    dados = resposta.json()
                    mandato_remoto = dados.get("mandato")

                    if type(mandato_remoto) is int:
                        self.persistencia.atualizar_mandato(
                            mandato_remoto
                        )

            except requests.RequestException:
                print(
                    f"[Eleicao] No {id_no} indisponivel",
                    flush=True
                )

        with self.lock:
            if numero != self.numero_eleicao:
                return

            if not self.eleicao_em_andamento:
                return

            if respondeu_superior:
                print(
                    f"[Eleicao] No {self.id_no} "
                    "aguardando coordenador",
                    flush=True
                )

                self.temporizador = threading.Timer(
                    self.tempo_espera,
                    self.verificar_timeout,
                    args=(numero,)
                )
                self.temporizador.daemon = True
                self.temporizador.start()
                return

        self.anunciar_lider(numero)

    def verificar_timeout(self, numero):
        with self.lock:
            if numero != self.numero_eleicao:
                return

            if not self.eleicao_em_andamento:
                return

            self.eleicao_em_andamento = False
            self.temporizador = None

        print(
            f"[Eleicao] Timeout no No {self.id_no}",
            flush=True
        )

        self.iniciar_em_thread()

    def receber_eleicao(self, origem, mandato):
        if origem >= self.id_no:
            return False

        self.persistencia.atualizar_mandato(mandato)

        print(
            f"[Eleicao] No {self.id_no} recebeu "
            f"eleicao do No {origem}",
            flush=True
        )

        self.iniciar_em_thread()
        return True

    def anunciar_lider(self, numero):
        with self.lock:
            if numero != self.numero_eleicao:
                return

            if not self.eleicao_em_andamento:
                return

            mandato = self.persistencia.obter_mandato()

            self.lider_atual = self.id_no
            self.mandato_lider = mandato
            self.eleicao_em_andamento = False

            if self.temporizador is not None:
                self.temporizador.cancel()
                self.temporizador = None

        print(
            f"[Eleicao] No {self.id_no} assumiu "
            f"lideranca no mandato {mandato}",
            flush=True
        )

        for id_no, endereco in self.enderecos_nos.items():
            if id_no == self.id_no:
                continue

            try:
                requests.post(
                    f"{endereco}/coordenador",
                    json={
                        "lider": self.id_no,
                        "mandato": mandato
                    },
                    timeout=2
                )
            except requests.RequestException:
                print(
                    f"[Eleicao] Falha ao avisar No {id_no}",
                    flush=True
                )

    def receber_coordenador(self, id_lider, mandato):
        if id_lider not in self.enderecos_nos:
            return False

        with self.lock:
            mandato_local = self.persistencia.obter_mandato()

            # Rejeita anuncios de mandatos anteriores
            if mandato < mandato_local:
                print(
                    f"[Eleicao] Anuncio antigo rejeitado: "
                    f"mandato {mandato}",
                    flush=True
                )
                return False

            # No mesmo mandato, rejeita lider inferior
            if (
                mandato == self.mandato_lider
                and self.lider_atual is not None
                and id_lider < self.lider_atual
            ):
                return False

            self.persistencia.atualizar_mandato(mandato)

            self.lider_atual = id_lider
            self.mandato_lider = mandato
            self.eleicao_em_andamento = False
            self.numero_eleicao += 1

            if self.temporizador is not None:
                self.temporizador.cancel()
                self.temporizador = None

        print(
            f"[Eleicao] Lider atual: No {id_lider}, "
            f"mandato {mandato}",
            flush=True
        )

        return True
