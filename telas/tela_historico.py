from kivy.metrics import dp
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, TwoLineListItem
from kivymd.uix.screen import MDScreen
from kivy.uix.scrollview import ScrollView
from kivymd.uix.toolbar import MDTopAppBar


class TelaHistorico(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = MDBoxLayout(orientation='vertical')

        self.toolbar = MDTopAppBar(
            title='Histórico',
            left_action_items=[['arrow-left', lambda x: self._voltar()]],
        )
        root.add_widget(self.toolbar)

        scroll = ScrollView()
        self.lista = MDList()
        scroll.add_widget(self.lista)
        root.add_widget(scroll)

        self.add_widget(root)

    def carregar(self, ex):
        self.toolbar.title = f"Histórico — {ex['nome']}"
        self.lista.clear_widgets()

        app = MDApp.get_running_app()
        registros = app.historico.get(ex['id'], [])

        if not registros:
            self.lista.add_widget(MDLabel(
                text='Sem histórico ainda.',
                halign='center',
                size_hint_y=None,
                height=dp(60),
            ))
            return

        for reg in reversed(registros):
            self.lista.add_widget(TwoLineListItem(
                text=f"{reg['peso']} kg",
                secondary_text=reg['data'],
            ))

    def _voltar(self):
        MDApp.get_running_app().sm.current = 'treino'
