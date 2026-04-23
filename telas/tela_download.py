import os
import threading
import urllib.request

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.screen import MDScreen

_BASE_URL = (
    'https://raw.githubusercontent.com/'
    'marcosalexandredemedeiros-glitch/'
    'ronaldo-medeiros-fisiologista-videos/main/'
)

VIDEOS = [
    'abdominal.mp4',
    'abducao_quadril_com_caneleira.mp4',
    'abducao_quadril_maquina.mp4',
    'afundo.mp4',
    'agachamento_halteres.mp4',
    'agachamento_livre.mp4',
    'agachamento_no_step.mp4',
    'agachamento_smith.mp4',
    'bulgaro.mp4',
    'cadeira_abdutora.mp4',
    'cadeira_adutora.mp4',
    'cadeira_extensora.mp4',
    'cadeira_flexora.mp4',
    'cadeira_gemeos.mp4',
    'desenvolvimento_halteres.mp4',
    'elevacao_frontal.mp4',
    'elevacao_lateral.mp4',
    'elevacao_pelvica.mp4',
    'leg_press_45.mp4',
    'mesa_flexora.mp4',
    'panturrilhas_halteres.mp4',
    'panturrilhas_leg_press.mp4',
    'passada_alternada.mp4',
    'peck_deck.mp4',
    'prancha_isometrica.mp4',
    'pull_down.mp4',
    'pulley_fechado.mp4',
    'pulley_frente.mp4',
    'pulley_neutro.mp4',
    'pulley_supinado.mp4',
    'remada_neutra.mp4',
    'remada_neutra_maquina.mp4',
    'remada_pronada_maquina.mp4',
    'remada_sentada.mp4',
    'remada_supinada_maquina.mp4',
    'rosca_alternada.mp4',
    'rosca_barra_neutra.mp4',
    'rosca_barra_w.mp4',
    'rosca_concentrada.mp4',
    'rosca_direta_halteres.mp4',
    'rosca_pulley.mp4',
    'rosca_scott.mp4',
    'rotacao_manguito.mp4',
    'supino_declinado.mp4',
    'supino_halteres.mp4',
    'supino_inclinado_halteres.mp4',
    'supino_reto.mp4',
    'triceps_corda.mp4',
    'triceps_frances.mp4',
    'triceps_pulley.mp4',
    'triceps_testa.mp4',
    'voador_halteres.mp4',
]

_COR_ACCENT = get_color_from_hex('#5b9cf6')
_FLAG_FILE  = 'videos_ok.flag'


def pasta_videos():
    app = MDApp.get_running_app()
    if not app:
        return 'videos'
    return os.path.join(app.user_data_dir, 'videos')


def videos_prontos():
    app = MDApp.get_running_app()
    if not app:
        return False
    flag = os.path.join(app.user_data_dir, 'videos_ok.flag')
    return os.path.exists(flag)

    flag = os.path.join(MDApp.get_running_app().user_data_dir, _FLAG_FILE)
    return os.path.exists(flag)


def marcar_videos_prontos():
    flag = os.path.join(MDApp.get_running_app().user_data_dir, _FLAG_FILE)
    open(flag, 'w').close()


class TelaDownload(MDScreen):

    def on_enter(self):
        self._cancelado = False
        self._build_ui()
        threading.Thread(target=self._baixar, daemon=True).start()

    def _build_ui(self):
        self.clear_widgets()

        root = MDBoxLayout(
            orientation='vertical',
            padding=[Window.width * 0.08, Window.height * 0.08],
            spacing=Window.height * 0.025,
        )

        root.add_widget(MDLabel(
            text='Preparando seu app',
            font_style='H5',
            halign='center',
            size_hint_y=None,
            height=Window.height * 0.07,
        ))

        root.add_widget(MDLabel(
            text='Baixando vídeos demonstrativos dos exercícios.\nIsso acontece apenas uma vez.',
            halign='center',
            size_hint_y=None,
            height=Window.height * 0.08,
        ))

        self._lbl_video = MDLabel(
            text='Iniciando...',
            halign='center',
            font_style='Caption',
            size_hint_y=None,
            height=Window.height * 0.04,
        )
        root.add_widget(self._lbl_video)

        self._barra = MDProgressBar(
            value=0,
            size_hint_y=None,
            height=dp(8) if False else Window.height * 0.012,
            color=_COR_ACCENT,
        )
        root.add_widget(self._barra)

        self._lbl_contador = MDLabel(
            text=f'0 / {len(VIDEOS)}',
            halign='center',
            size_hint_y=None,
            height=Window.height * 0.04,
        )
        root.add_widget(self._lbl_contador)

        root.add_widget(MDBoxLayout(size_hint_y=1))  # espaçador

        btn_pular = MDFlatButton(
            text='Pular (vídeos não estarão disponíveis)',
            size_hint=(1, None),
            height=Window.height * 0.06,
            on_release=lambda _: self._pular(),
        )
        root.add_widget(btn_pular)

        self.add_widget(root)

    def _baixar(self):
        pasta = pasta_videos()
        os.makedirs(pasta, exist_ok=True)
        total = len(VIDEOS)

        for i, nome in enumerate(VIDEOS):
            if self._cancelado:
                return
            destino = os.path.join(pasta, nome)
            if not os.path.exists(destino):
                try:
                    urllib.request.urlretrieve(_BASE_URL + nome, destino + '.tmp')
                    os.rename(destino + '.tmp', destino)
                except Exception:
                    # Remove arquivo parcial se houver erro
                    try:
                        os.remove(destino + '.tmp')
                    except OSError:
                        pass
            Clock.schedule_once(lambda dt, n=nome, idx=i: self._atualizar(idx + 1, total, n))

        if not self._cancelado:
            Clock.schedule_once(lambda dt: self._concluido())

    def _atualizar(self, atual, total, nome):
        nome_legivel = nome.replace('.mp4', '').replace('_', ' ').title()
        self._lbl_video.text    = nome_legivel
        self._lbl_contador.text = f'{atual} / {total}'
        self._barra.value       = (atual / total) * 100

    def _concluido(self):
        marcar_videos_prontos()
        self._ir_para_proxima()

    def _pular(self):
        self._cancelado = True
        self._ir_para_proxima()

    def _ir_para_proxima(self):
        app = MDApp.get_running_app()
        app.sm.current = 'home' if app.cliente else 'cadastro'
