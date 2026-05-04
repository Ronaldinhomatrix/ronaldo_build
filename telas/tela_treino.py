import os
import unicodedata
import platform
import threading
import re
import shutil

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
        import unicodedata
        import re
        sem_acento = unicodedata.normalize('NFD', nome)
        sem_acento = ''.join(c for c in sem_acento if unicodedata.category(c) != 'Mn')
        arquivo = sem_acento.lower().strip()
        arquivo = re.sub(r'[^a-z0-9\s_]', '', arquivo)
        arquivo = arquivo.replace(' ', '_') + '.mp4'
        return os.path.join('assets', 'videos', arquivo)

    def __init__(self, ex, tela, **kwargs):
        super().__init__(
            orientation='horizontal', size_hint=(1, None), padding=0, spacing=0,
            ripple_behavior=True, md_bg_color=get_color_from_hex('#2C2C2E'),
            radius=[dp(12)], elevation=2, **kwargs
        )
        self.ex = ex
        self.tela = tela
        app = MDApp.get_running_app()
        self._feito = app.progresso_treino.get('feitos', {}).get(ex.get('id', ''), False)
        self._cor_pendente = COR_PENDENTE
        self._tem_video = True # Assume que tem para mostrar o icone
        self._build()

    def _build(self):
        borda = MDBoxLayout(size_hint=(None, 1), width=dp(4), md_bg_color=COR_ACCENT)
        self.add_widget(borda)
        conteudo = MDBoxLayout(orientation='vertical', size_hint=(1, None), padding=[dp(10), 0, dp(10), dp(10)])
        conteudo.bind(minimum_height=conteudo.setter('height'))
        conteudo.bind(height=self.setter('height'))

        linha1 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(45), md_bg_color=get_color_from_hex('#5DADE2'))
        lbl_nome = Label(text=self.ex['nome'], font_size='18sp', size_hint_x=1, halign='left', valign='middle')
        lbl_nome.bind(size=lbl_nome.setter('text_size'))
        linha1.add_widget(lbl_nome)
        
        btn_play = MDIconButton(icon='play-circle-outline', theme_text_color='Custom', text_color=(1,1,1,1), on_release=lambda x: self.tela._ver_midia(self.ex))
        linha1.add_widget(btn_play)
        conteudo.add_widget(linha1)

        obs_trainer = self.ex.get('obs_trainer', '').strip()
        if obs_trainer:
            conteudo.add_widget(MDLabel(text=obs_trainer, font_style='Caption', italic=True, theme_text_color='Custom', text_color=COR_ACCENT, size_hint_y=None, height=dp(30)))

        linha2 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40))
        linha2.add_widget(MDLabel(text=f"Séries: {self.ex.get('series','')}", size_hint_x=0.5))
        linha2.add_widget(MDLabel(text=f"Peso: {self.ex.get('peso','')} kg", halign='right'))
        conteudo.add_widget(linha2)

        linha3 = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(50), spacing=dp(10))
        tem_obs = bool(self.ex.get('obs', '').strip())
        self._btn_obs = MDRaisedButton(text='Obs.' if not tem_obs else 'Obs. OK', md_bg_color=COR_CONCLUIDO if tem_obs else self._cor_pendente, on_release=lambda x: self.tela._editar_obs(self.ex, self))
        self._btn_feito = MDRaisedButton(text='✓ Feito' if self._feito else 'Feito', md_bg_color=COR_CONCLUIDO if self._feito else self._cor_pendente, on_release=self._toggle_feito)
        linha3.add_widget(self._btn_obs)
        linha3.add_widget(MDBoxLayout(size_hint_x=1))
        linha3.add_widget(self._btn_feito)
        conteudo.add_widget(linha3)
        self.add_widget(conteudo)

    def _toggle_feito(self, *args):
        self._feito = not self._feito
        app = MDApp.get_running_app()
        app.progresso_treino.setdefault('feitos', {})[self.ex['id']] = self._feito
        self._btn_feito.text = '✓ Feito' if self._feito else 'Feito'
        self._btn_feito.md_bg_color = COR_CONCLUIDO if self._feito else self._cor_pendente
        self.tela._verificar_conclusao()

class TelaTreino(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cards = []
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')
        self.toolbar = MDTopAppBar(title='Treino', md_bg_color=get_color_from_hex('#1A1A1A'), left_action_items=[['arrow-left', lambda x: self._voltar()]])
        root.add_widget(self.toolbar)
        scroll = ScrollView()
        self.lista = MDBoxLayout(orientation='vertical', spacing=dp(15), padding=dp(15), size_hint_y=None)
        self.lista.bind(minimum_height=self.lista.setter('height'))
        scroll.add_widget(self.lista)
        root.add_widget(scroll)
        self._btn_concluir = MDRaisedButton(text='Registrar treino completo', size_hint=(1, None), height=dp(56), on_release=lambda x: self._confirmar_conclusao())
        root.add_widget(self._btn_concluir)
        self.add_widget(root)

    def carregar(self, treino):
        self.treino_atual = treino
        app = MDApp.get_running_app()
        self.toolbar.title = f"Treino {treino}"
        self.lista.clear_widgets()
        self._cards = []
        for ex in app.treinos.get(treino, []):
            card = CardExercicio(ex=ex, tela=self)
            self._cards.append(card)
            self.lista.add_widget(card)
        self._verificar_conclusao()

    def _verificar_conclusao(self):
        if not self._cards: return
        todos = all(c._feito for c in self._cards)
        self._btn_concluir.md_bg_color = COR_CONCLUIDO if todos else (0.2, 0.2, 0.25, 1)

    def _confirmar_conclusao(self):
        self._executar_conclusao()

    def _executar_conclusao(self):
        app = MDApp.get_running_app()
        app.salvar(treino=self.treino_atual, exercicios_concluidos=[c.ex for c in self._cards], on_success=lambda: setattr(app.sm, 'current', 'home'))

    def _editar_obs(self, ex, card):
        campo = MDTextField(text=ex.get('obs', ''), hint_text='Sua observação', multiline=True)
        dlg = MDDialog(title=ex['nome'], type='custom', content_cls=campo, buttons=[
            MDFlatButton(text='CANCELAR', on_release=lambda x: dlg.dismiss()),
            MDRaisedButton(text='SALVAR', on_release=lambda x: self._salvar_obs(ex, card, campo.text, dlg)),
        ])
        dlg.open()

    def _salvar_obs(self, ex, card, texto, dlg):
        ex['obs'] = texto.strip()
        app = MDApp.get_running_app()
        app.salvar()
        dlg.dismiss()
        
        if ex['obs'] and app.cliente:
            card._btn_obs.text = 'Enviando...'
            import firebase_sync
            firebase_sync.notificar_obs(app.cliente['nome'], ex['nome'], ex['obs'], 
                                       on_success=lambda: self._on_obs_sucesso(card),
                                       on_error=lambda m: self._on_obs_erro(card, m))
            firebase_sync.salvar_dados(app.cliente['id'], app.historico, app.atividade, {ex['id']: ex['obs']})

    def _on_obs_sucesso(self, card):
        card._btn_obs.text = 'Obs. OK'
        card._btn_obs.md_bg_color = COR_CONCLUIDO

    def _on_obs_erro(self, card, msg):
        card._btn_obs.text = 'Erro'
        card._btn_obs.md_bg_color = (0.8, 0, 0, 1)

    def _ver_midia(self, ex):
        app = MDApp.get_running_app()
        caminho_asset = CardExercicio._caminho_video(ex.get('nome', ''))
        nome_arquivo = os.path.basename(caminho_asset)
        caminho_final = os.path.join(app.user_data_dir, nome_arquivo)

        def _abrir(dt):
            try:
                from kivy.uix.videoplayer import VideoPlayer
                player = VideoPlayer(source=caminho_final, state='play', options={'eos': 'loop'})
                pop = Popup(title=ex['nome'], content=player, size_hint=(0.9, 0.8))
                pop.bind(on_dismiss=lambda x: setattr(player, 'state', 'stop'))
                pop.open()
            except Exception as e:
                MDDialog(text=f"Erro: {e}").open()

        try:
            if not os.path.exists(caminho_final) or os.path.getsize(caminho_final) < 100:
                with open(caminho_asset, 'rb') as f_in, open(caminho_final, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            Clock.schedule_once(_abrir, 1.0)
        except:
            MDDialog(text="Video nao encontrado").open()

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
