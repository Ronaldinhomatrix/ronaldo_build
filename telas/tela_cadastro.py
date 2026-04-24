"""
Tela de cadastro inicial do cliente.
Exibida apenas na primeira execução (quando cliente.json não existe).
"""
import json
import os
import uuid
import threading

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.clock import Clock
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
        root.add_widget(MDBoxLayout(size_hint_y=0.2))

        # Aumentada a altura do cabeçalho para não achatar os textos
        cabecalho = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(180), 
            spacing=dp(5),
        )
        cabecalho.add_widget(MDLabel(
            text='Seja Bem Vindo à Plataforma Oficial do',
            halign='center',
            font_style='Subtitle1',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(30),
        ))
        
        # Nome Ronaldo Medeiros como o MAIOR destaque
        cabecalho.add_widget(MDLabel(
            text='Ronaldo Medeiros',
            halign='center',
            font_style='H3', # Estilo gigante nativo
            bold=True,
            size_hint_y=None,
            height=dp(70),
        ))
        
        cabecalho.add_widget(MDLabel(
            text='Fisiologista',
            halign='center',
            font_style='H5',
            theme_text_color='Custom',
            text_color=(0.357, 0.612, 0.965, 1),
            size_hint_y=None,
            height=dp(40),
        ))
        root.add_widget(cabecalho)
        
        root.add_widget(MDBoxLayout(size_hint_y=None, height=dp(20)))
        
        root.add_widget(MDLabel(
            text='Preparamos um ambiente exclusivo para gerenciar seus treinos e sua evolução.',
            halign='center',
            font_style='H6',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(60),
        ))
        
        root.add_widget(MDLabel(
            text='Para configurar seu acesso exclusivo, digite seu nome completo.',
            halign='center',
            font_style='Subtitle1',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(40),
        ))

        self._campo_nome = MDTextField(
            hint_text='Nome completo',
            size_hint_x=1,
            font_size='20sp',
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
            height=dp(56),
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

        self._lbl_erro.theme_text_color = 'Secondary'
        self._lbl_erro.text = 'Verificando cadastro...'
        
        threading.Thread(target=self._processar_cadastro, args=(nome,), daemon=True).start()

    def _processar_cadastro(self, nome):
        app = MDApp.get_running_app()
        
        # 1. Busca por nome no Firebase
        cliente_id_existente = firebase_sync.buscar_id_por_nome(nome)
        
        if cliente_id_existente:
            cliente_id = cliente_id_existente
            # 2. SE EXISTE, BAIXA OS DADOS NA HORA
            dados = firebase_sync.buscar_cliente_completo(cliente_id)
            if dados:
                app.treinos = dados.get('treinos', {})
                app.treinos_nomes = dados.get('treinos_nomes', {})
                app.treino_atual = dados.get('treino_atual', '')
        else:
            cliente_id = str(uuid.uuid4())
            app.treinos = {}
            app.treinos_nomes = {}

        app.cliente = {'id': cliente_id, 'nome': nome}

        # 3. Salva arquivos locais
        try:
            with open(app.cliente_file, 'w', encoding='utf-8') as f:
                json.dump(app.cliente, f, ensure_ascii=False, indent=2)
            with open(app.treinos_file, 'w', encoding='utf-8') as f:
                json.dump(app.treinos, f, ensure_ascii=False, indent=2)
            with open(app.treinos_nomes_file, 'w', encoding='utf-8') as f:
                json.dump(app.treinos_nomes, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar: {e}")

        # 4. Se for novo, registra no banco
        if not cliente_id_existente:
            firebase_sync.criar_cliente(cliente_id, nome)

        # 5. Finaliza
        Clock.schedule_once(lambda dt: self._finalizar_cadastro(), 0)

    def _finalizar_cadastro(self):
        app = MDApp.get_running_app()
        app.sm.current = 'home'
