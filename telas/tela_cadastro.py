"""
Tela de cadastro inicial do cliente.
Exibida apenas na primeira execução (quando cliente.json não existe).
"""
import json
import os
import uuid

from kivy.core.window import Window
from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField

import firebase_sync


class TelaCadastro(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def on_enter(self):
        Window.softinput_mode = 'below_target'

    def on_leave(self):
        Window.softinput_mode = ''

    def _build(self):
        root = MDBoxLayout(
            orientation='vertical',
            padding=dp(40),
            spacing=dp(20),
        )
        root.add_widget(MDBoxLayout(size_hint_y=0.25))

        cabecalho = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(116),
            spacing=0,
        )
        cabecalho.add_widget(MDLabel(
            text='Seja Bem Vindo à Plataforma Oficial do',
            halign='center',
            font_style='Subtitle1',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(28),
        ))
        cabecalho.add_widget(MDLabel(
            text='Ronaldo Medeiros',
            halign='center',
            font_size='36sp',
            size_hint_y=None,
            height=dp(52),
        ))
        cabecalho.add_widget(MDLabel(
            text='Fisiologista',
            halign='center',
            font_style='H6',
            theme_text_color='Custom',
            text_color=(0.357, 0.612, 0.965, 1),
            size_hint_y=None,
            height=dp(36),
        ))
        root.add_widget(cabecalho)
        root.add_widget(MDBoxLayout(size_hint_y=None, height=dp(24)))
        root.add_widget(MDLabel(
            text='Preparamos um ambiente exclusivo para\ngerenciar seus treinos e sua evolução.',
            halign='center',
            font_style='Body1',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(56),
        ))
        root.add_widget(MDLabel(
            text='Para configurar seu acesso exclusivo,\ndigite seu nome completo.',
            halign='center',
            font_style='Body2',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(48),
        ))

        self._campo_nome = MDTextField(
            hint_text='Nome completo',
            size_hint_x=1,
        )
        root.add_widget(self._campo_nome)

        self._lbl_erro = MDLabel(
            text='',
            halign='center',
            theme_text_color='Error',
            size_hint_y=None,
            height=dp(30),
        )
        root.add_widget(self._lbl_erro)

        root.add_widget(MDRaisedButton(
            text='COMEÇAR',
            size_hint=(1, None),
            height=dp(48),
            rounded_button=True,
            on_release=lambda x: self._cadastrar(),
        ))
        root.add_widget(MDBoxLayout(size_hint_y=1))
        self.add_widget(root)

    def _cadastrar(self):
        nome = self._campo_nome.text.strip()
        if not nome:
            self._lbl_erro.text = 'Digite seu nome para continuar.'
            return

        app = MDApp.get_running_app()
        cliente_id = str(uuid.uuid4())
        app.cliente = {'id': cliente_id, 'nome': nome}

        with open(app.CLIENTE_FILE, 'w', encoding='utf-8') as f:
            json.dump(app.cliente, f, ensure_ascii=False, indent=2)

        # Zera dados locais de qualquer cliente anterior
        import main as _main
        app.treinos   = {}
        app.historico = {}
        app.atividade = []
        with open(_main.TREINOS_FILE,   'w', encoding='utf-8') as f:
            json.dump(app.treinos,   f, ensure_ascii=False, indent=2)
        with open(_main.HISTORICO_FILE, 'w', encoding='utf-8') as f:
            json.dump(app.historico, f, ensure_ascii=False, indent=2)
        with open(_main.ATIVIDADE_FILE, 'w', encoding='utf-8') as f:
            json.dump(app.atividade, f, ensure_ascii=False, indent=2)

        # Salva backup na Downloads para sobreviver a reinstalações
        backup_path = _main._pasta_downloads()
        try:
            os.makedirs(backup_path, exist_ok=True)
            backup_file = os.path.join(backup_path, 'ronaldo_cliente_backup.json')
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(app.cliente, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f'[Backup] Não foi possível salvar backup: {e}')

        # Cria documento no Firestore (background)
        firebase_sync.criar_cliente(cliente_id, nome)

        app.sm.current = 'home'
