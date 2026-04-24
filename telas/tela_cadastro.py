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
            font_style='H5',  # Aumentado para H5 (Impacto)
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(36),
        ))
        cabecalho.add_widget(MDLabel(
            text='Ronaldo Medeiros',
            halign='center',
            font_size='45sp', # Aumentado levemente para 45sp
            bold=True,
            size_hint_y=None,
            height=dp(62),
        ))
        cabecalho.add_widget(MDLabel(
            text='Fisiologista',
            halign='center',
            font_style='H5', # Aumentado para H5 (Acompanha o nome)
            theme_text_color='Custom',
            text_color=(0.357, 0.612, 0.965, 1),
            size_hint_y=None,
            height=dp(40),
        ))
        root.add_widget(cabecalho)
        root.add_widget(MDBoxLayout(size_hint_y=None, height=dp(30)))
        root.add_widget(MDLabel(
            text='Preparamos um ambiente exclusivo para gerenciar seus treinos e sua evolução.',
            halign='center',
            font_style='H6', # Aumentado para H6 (Leitura confortável)
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(64),
        ))
        root.add_widget(MDLabel(
            text='Para configurar seu acesso exclusivo, digite seu nome completo.',
            halign='center',
            font_style='Subtitle1', # Aumentado
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(52),
        ))

        self._campo_nome = MDTextField(
            hint_text='Nome completo',
            size_hint_x=1,
            font_size='18sp', # Texto de digitação maior
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

        self._lbl_erro.theme_text_color = 'Secondary'
        self._lbl_erro.text = 'Verificando cadastro...'
        
        # Rodamos a busca em uma thread para não travar a tela
        import threading
        threading.Thread(target=self._processar_cadastro, args=(nome,), daemon=True).start()

    def _processar_cadastro(self, nome):
        from kivy.clock import Clock
        app = MDApp.get_running_app()
        
        # 1. Tenta encontrar o ID existente por nome
        cliente_id_existente = firebase_sync.buscar_id_por_nome(nome)
        
        if cliente_id_existente:
            cliente_id = cliente_id_existente
            print(f"[Cadastro] Cliente encontrado! Usando ID: {cliente_id}")
        else:
            cliente_id = str(uuid.uuid4())
            print(f"[Cadastro] Novo cliente. Gerado ID: {cliente_id}")

        # 2. Atualiza o objeto do app
        app.cliente = {'id': cliente_id, 'nome': nome}

        # 3. Salva os arquivos locais
        try:
            with open(app.cliente_file, 'w', encoding='utf-8') as f:
                json.dump(app.cliente, f, ensure_ascii=False, indent=2)

            # Prepara arquivos de dados se não existirem
            app.treinos   = {}
            app.historico = {}
            app.atividade = []
            
            with open(app.treinos_file, 'w', encoding='utf-8') as f:
                json.dump(app.treinos, f, ensure_ascii=False, indent=2)
            with open(app.historico_file, 'w', encoding='utf-8') as f:
                json.dump(app.historico, f, ensure_ascii=False, indent=2)
            with open(app.atividade_file, 'w', encoding='utf-8') as f:
                json.dump(app.atividade, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar arquivos iniciais: {e}")

        # 4. Se for novo, cria no Firestore. Se for antigo, apenas garante que os dados estão lá.
        if not cliente_id_existente:
            firebase_sync.criar_cliente(cliente_id, nome)

        # 5. Vai para a Home na thread principal
        Clock.schedule_once(lambda dt: self._finalizar_cadastro(), 0)

    def _finalizar_cadastro(self):
        app = MDApp.get_running_app()
        app.sm.current = 'home'
