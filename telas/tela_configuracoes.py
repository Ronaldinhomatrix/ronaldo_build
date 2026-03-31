import glob
import os
import zipfile
from datetime import datetime

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.toolbar import MDTopAppBar

from main import DATA_DIR, TREINOS_FILE, HISTORICO_FILE, ATIVIDADE_FILE, _pasta_downloads


class TelaConfiguracoes(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dialog = None
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')

        root.add_widget(MDTopAppBar(
            title='Configurações',
            left_action_items=[['arrow-left', lambda x: self._voltar()]],
        ))

        content = MDBoxLayout(
            orientation='vertical',
            padding=dp(24),
            spacing=dp(12),
        )

        # ── seção de backup ───────────────────────────────────────────────────
        content.add_widget(MDLabel(
            text='Backup de dados',
            font_style='Subtitle1',
            size_hint_y=None,
            height=dp(32),
        ))

        content.add_widget(MDLabel(
            text='Exporta os treinos, histórico de pesos e histórico de\natividade para um arquivo ZIP na pasta Downloads.',
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(40),
        ))

        content.add_widget(MDRaisedButton(
            text='Exportar backup',
            size_hint=(1, None),
            height=dp(48),
            on_release=lambda x: self._exportar(),
        ))

        content.add_widget(MDBoxLayout(size_hint_y=None, height=dp(8)))

        content.add_widget(MDLabel(
            text='Restaura os dados a partir de um backup salvo em Downloads.\nAtenção: substitui todos os dados atuais.',
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(40),
        ))

        content.add_widget(MDRaisedButton(
            text='Importar backup',
            size_hint=(1, None),
            height=dp(48),
            on_release=lambda x: self._abrir_dialogo_importar(),
        ))

        # ── status ────────────────────────────────────────────────────────────
        self._lbl_status = MDLabel(
            text='',
            halign='center',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(48),
        )
        content.add_widget(self._lbl_status)

        content.add_widget(MDBoxLayout(size_hint_y=1))

        # ── créditos ──────────────────────────────────────────────────────────
        content.add_widget(MDLabel(
            text='Desenvolvido por',
            halign='center',
            font_style='Caption',
            theme_text_color='Secondary',
            size_hint_y=None,
            height=dp(20),
        ))
        content.add_widget(MDLabel(
            text='[color=#FFFFFF]Operant[/color][color=#5b9cf6]Lab[/color]',
            markup=True,
            halign='center',
            font_name='ErasBoldITC',
            theme_text_color='Custom',
            text_color=(1, 1, 1, 1),
            size_hint_y=None,
            height=dp(28),
        ))

        root.add_widget(content)
        self.add_widget(root)

    # ── exportar ──────────────────────────────────────────────────────────────

    def _exportar(self):
        app = MDApp.get_running_app()
        app.salvar()  # garante que treinos e historico estão no disco

        downloads = _pasta_downloads()
        os.makedirs(downloads, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        destino = os.path.join(downloads, f'ronaldo_backup_{timestamp}.zip')

        try:
            with zipfile.ZipFile(destino, 'w', zipfile.ZIP_DEFLATED) as zf:
                for caminho in [TREINOS_FILE, HISTORICO_FILE, ATIVIDADE_FILE]:
                    if os.path.exists(caminho):
                        zf.write(caminho, arcname=os.path.basename(caminho))
            self._lbl_status.text = f'✓ Salvo em Downloads:\n{os.path.basename(destino)}'
        except Exception as e:
            self._lbl_status.text = f'Erro ao exportar:\n{e}'

    # ── importar ──────────────────────────────────────────────────────────────

    def _listar_backups(self):
        padrao = os.path.join(_pasta_downloads(), 'ronaldo_backup_*.zip')
        return sorted(glob.glob(padrao), reverse=True)  # mais recente primeiro

    def _abrir_dialogo_importar(self):
        backups = self._listar_backups()

        if not backups:
            self._lbl_status.text = 'Nenhum backup encontrado em Downloads.'
            return

        lista = MDBoxLayout(
            orientation='vertical',
            spacing=dp(2),
            size_hint_y=None,
        )
        lista.bind(minimum_height=lista.setter('height'))

        for caminho in backups:
            nome = os.path.basename(caminho)
            btn = MDFlatButton(
                text=nome,
                size_hint=(1, None),
                height=dp(44),
            )
            btn.bind(on_release=lambda x, c=caminho: self._selecionar(c))
            lista.add_widget(btn)

        scroll = ScrollView(size_hint_y=None, height=dp(min(len(backups) * 48, 240)))
        scroll.add_widget(lista)

        self._dialog = MDDialog(
            title='Selecionar backup',
            type='custom',
            content_cls=scroll,
            buttons=[
                MDFlatButton(
                    text='CANCELAR',
                    on_release=lambda x: self._dialog.dismiss(),
                ),
            ],
        )
        self._dialog.open()

    def _selecionar(self, caminho):
        self._dialog.dismiss()
        self._importar(caminho)

    def _importar(self, caminho):
        app = MDApp.get_running_app()
        esperados = {'treinos.json', 'historico.json', 'historico_atividade.json'}

        try:
            with zipfile.ZipFile(caminho, 'r') as zf:
                nomes = set(zf.namelist())
                faltando = esperados - nomes
                if faltando:
                    self._lbl_status.text = f'ZIP inválido. Faltam: {", ".join(faltando)}'
                    return
                zf.extractall(DATA_DIR)

            app.recarregar_dados()
            self._lbl_status.text = '✓ Backup restaurado com sucesso!'
            app.sm.current = 'home'

        except zipfile.BadZipFile:
            self._lbl_status.text = 'Erro: arquivo ZIP corrompido.'
        except Exception as e:
            self._lbl_status.text = f'Erro ao importar:\n{e}'

    # ── navegação ─────────────────────────────────────────────────────────────

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'home'
