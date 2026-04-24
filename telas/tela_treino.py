import os
import unicodedata

from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.toolbar import MDTopAppBar

COR_CONCLUIDO = get_color_from_hex('#2ECC71')
COR_ACCENT    = get_color_from_hex('#3498DB')
COR_OBS       = get_color_from_hex('#F1C40F')
COR_PENDENTE  = get_color_from_hex('#3D3D3D')


class CardExercicio(MDCard):
    @staticmethod
    def _caminho_video(nome):
        sem_acento = unicodedata.normalize('NFD', nome)
        sem_acento = ''.join(c for c in sem_acento if unicodedata.category(c) != 'Mn')
        arquivo = sem_acento.lower().replace(' ', '_') + '.mp4'
        from telas.tela_download import pasta_videos
        externo = os.path.join(pasta_videos(), arquivo)
        if os.path.exists(externo):
            return externo
        return os.path.join('assets', 'videos', arquivo)

    def __init__(self, ex, tela, **kwargs):
        super().__init__(
            orientation='horizontal',
            size_hint=(1, None),
            ripple_behavior=True,
            md_bg_color=get_color_from_hex('#2C2C2E'),
            radius=[dp(12), dp(12), dp(12), dp(12)],
            elevation=2,
            **kwargs,
        )
        self.ex = ex
        self.tela = tela
        app = MDApp.get_running_app()
        self._feito = False
        self._cor_pendente = COR_PENDENTE
        self._tem_video = os.path.exists(self._caminho_video(ex.get('nome', '')))
        self._build()

    def _build(self):
        borda = MDBoxLayout(size_hint=(None, 1), width=dp(4), md_bg_color=COR_ACCENT)
        self.add_widget(borda)

        conteudo = MDBoxLayout(orientation='vertical', size_hint=(1, None), padding=dp(10), spacing=dp(5))
        conteudo.bind(minimum_height=conteudo.setter('height'))
        self.bind(height=conteudo.setter('height'))

        linha1 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        linha1.add_widget(MDLabel(text=self.ex['nome'], font_style='H6', bold=True))
        
        if self._tem_video:
            linha1.add_widget(MDIconButton(
                icon='play-circle-outline',
                on_release=lambda x: self.tela._ver_midia(self.ex),
            ))
        conteudo.add_widget(linha1)

        info = f"Séries: {self.ex.get('series','')}  •  Peso: {self.ex.get('peso','')}kg"
        conteudo.add_widget(MDLabel(text=info, font_style='Body1', theme_text_color='Secondary'))

        self._btn_feito = MDRaisedButton(
            text='Feito',
            size_hint=(1, None),
            height=dp(40),
            md_bg_color=self._cor_pendente,
            on_release=self._toggle_feito
        )
        conteudo.add_widget(self._btn_feito)
        self.add_widget(conteudo)

    def _toggle_feito(self, *args):
        self._feito = not self._feito
        self._btn_feito.text = '✓ Concluído' if self._feito else 'Feito'
        self._btn_feito.md_bg_color = COR_CONCLUIDO if self._feito else self._cor_pendente
        self.tela._verificar_conclusao()


class TelaTreino(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cards = []
        self._build()

    def _build(self):
        layout = MDBoxLayout(orientation='vertical')
        self.toolbar = MDTopAppBar(title='Treino', left_action_items=[['arrow-left', lambda x: self._voltar()]])
        layout.add_widget(self.toolbar)

        scroll = ScrollView()
        self.lista = MDBoxLayout(orientation='vertical', spacing=dp(15), padding=dp(15), size_hint_y=None)
        self.lista.bind(minimum_height=self.lista.setter('height'))
        scroll.add_widget(self.lista)
        layout.add_widget(scroll)

        self._btn_concluir = MDRaisedButton(
            text='CONCLUIR TREINO',
            size_hint=(1, None),
            height=dp(56),
            on_release=lambda x: self._concluir()
        )
        layout.add_widget(self._btn_concluir)
        self.add_widget(layout)

    def carregar(self, treino):
        self.treino_atual = treino
        app = MDApp.get_running_app()
        self.toolbar.title = f"Treino {treino}"
        self.lista.clear_widgets()
        self._cards = []
        for ex in app.treinos.get(treino, []):
            card = CardExercicio(ex, self)
            self._cards.append(card)
            self.lista.add_widget(card)

    def _verificar_conclusao(self):
        pass

    def _concluir(self):
        app = MDApp.get_running_app()
        exercicios = [c.ex for c in self._cards]
        app.salvar(treino=self.treino_atual, exercicios_concluidos=exercicios)
        self._voltar()

    def _ver_midia(self, ex):
        try:
            from kivy.uix.videoplayer import VideoPlayer
            caminho = CardExercicio._caminho_video(ex.get('nome', ''))
            
            if not os.path.exists(caminho):
                raise Exception("Vídeo não encontrado.")

            # CONFIGURAÇÃO PROFISSIONAL PARA CELULAR (Vertical):
            # allow_stretch=True + keep_ratio=True: Garante que o vídeo cresça sem se deformar.
            player = VideoPlayer(
                source=caminho, 
                state='play',
                allow_stretch=True,
                options={'eos': 'loop', 'keep_ratio': True}
            )
            
            # Popup vertical gigante para ocupar 90% da altura da tela
            popup = Popup(
                title=ex['nome'], 
                content=player, 
                size_hint=(0.9, 0.9)
            )
            popup.bind(on_dismiss=lambda p: setattr(player, 'state', 'stop'))
            popup.open()
        except Exception as e:
            self.dialog = MDDialog(
                title="Vídeo Indisponível",
                text="Ocorreu um erro ao reproduzir o vídeo neste dispositivo.",
                buttons=[MDRaisedButton(text="OK", on_release=lambda x: self.dialog.dismiss())]
            )
            self.dialog.open()

    def _voltar(self):
        self.manager.current = 'home'
