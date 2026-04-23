import json
import os
import platform
import threading
import uuid
from datetime import datetime

# Configurações iniciais
if platform.system() == 'Windows':
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

os.environ['KIVY_VIDEO'] = 'ffpyplayer'

from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivymd.app import MDApp

import firebase_sync

def _pasta_downloads():
    if platform.system() == 'Android':
        return '/storage/emulated/0/Download'
    return os.path.join(os.path.expanduser('~'), 'Downloads')

class RonaldoMedeirosFisiologistaApp(MDApp):
    def build(self):
        self.title = 'Ronaldo Medeiros Fisiologista'
        self.theme_cls.primary_palette = 'BlueGray'
        self.theme_cls.theme_style = 'Dark'
        self.theme_cls.primary_hue = '500'

        # DEFINIÇÃO DINÂMICA DE CAMINHOS (Crucial para Android)
        # user_data_dir é a única pasta com permissão de escrita garantida
        self.data_dir = self.user_data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.treinos_file       = os.path.join(self.data_dir, 'treinos.json')
        self.treinos_nomes_file = os.path.join(self.data_dir, 'treinos_nomes.json')
        self.historico_file     = os.path.join(self.data_dir, 'historico.json')
        self.atividade_file     = os.path.join(self.data_dir, 'historico_atividade.json')
        self.cliente_file       = os.path.join(self.data_dir, 'cliente.json')
        self.sync_file          = os.path.join(self.data_dir, 'ultima_sync.json')
        self._CLIENTE_BACKUP    = os.path.join(_pasta_downloads(), 'ronaldo_cliente_backup.json')

        # Registro de Fonte seguro
        try:
            font_path = os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'ERASBD.TTF')
            if os.path.exists(font_path):
                LabelBase.register(name='ErasBoldITC', fn_regular=font_path)
        except Exception as e:
            print(f"Erro ao carregar fonte: {e}")

        self.pode_editar      = True
        self.treino_atual     = ''
        self.progresso_treino = {}
        
        # Carregamento de dados
        self.cliente       = self._carregar(self.cliente_file, None) or self._recuperar_cliente_downloads()
        self.treinos       = self._carregar(self.treinos_file,       {})
        self.treinos_nomes = self._carregar(self.treinos_nomes_file, {})
        self.historico     = self._carregar(self.historico_file,     {})
        self.atividade     = self._carregar(self.atividade_file,     [])

        # Importação tardia para evitar lentidão no loading
        from telas.tela_cadastro import TelaCadastro
        from telas.tela_home import TelaHome
        from telas.tela_treino import TelaTreino
        from telas.tela_historico import TelaHistorico
        from telas.tela_atividade import TelaAtividade
        from telas.tela_configuracoes import TelaConfiguracoes
        from telas.tela_download import TelaDownload, videos_prontos

        self.sm = ScreenManager(transition=SlideTransition())
        self.sm.add_widget(TelaDownload(name='download'))
        self.sm.add_widget(TelaCadastro(name='cadastro'))
        self.sm.add_widget(TelaHome(name='home'))
        self.sm.add_widget(TelaTreino(name='treino'))
        self.sm.add_widget(TelaHistorico(name='historico'))
        self.sm.add_widget(TelaAtividade(name='atividade'))
        self.sm.add_widget(TelaHome(name='configuracoes')) # Fallback simples

        if not videos_prontos():
            self.sm.current = 'download'
        elif self.cliente:
            self.sm.current = 'home'
        else:
            self.sm.current = 'cadastro'
            
        return self.sm

    def on_start(self):
        if self.cliente:
            threading.Thread(target=self._puxar_treinos_firebase, daemon=True).start()
            Clock.schedule_interval(self._verificar_sync_diario, 60)

    def _carregar(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return default

    def _recuperar_cliente_downloads(self):
        dados = self._carregar(self._CLIENTE_BACKUP, None)
        if not (dados and dados.get('id')): return None
        cliente = {'id': dados['id'], 'nome': dados['nome']}
        try:
            with open(self.cliente_file, 'w', encoding='utf-8') as f:
                json.dump(cliente, f, ensure_ascii=False)
        except: pass
        return cliente

    def salvar(self, treino=None, exercicios_concluidos=None):
        try:
            if treino and exercicios_concluidos:
                agora = datetime.now()
                for ex in exercicios_concluidos:
                    self.atividade.append({
                        'data': agora.strftime('%d/%m/%Y'),
                        'nome': ex['nome'],
                        'peso': ex.get('peso', ''),
                        'concluido': True,
                    })
                with open(self.atividade_file, 'w', encoding='utf-8') as f:
                    json.dump(self.atividade, f, ensure_ascii=False)

            with open(self.treinos_file, 'w', encoding='utf-8') as f:
                json.dump(self.treinos, f, ensure_ascii=False)
            
            # Sincronização Firebase
            if self.cliente:
                firebase_sync.salvar_dados(self.cliente['id'], self.historico, self.atividade)
        except Exception as e:
            print(f"Erro ao salvar: {e}")

    def _puxar_treinos_firebase(self):
        try:
            dados = firebase_sync.buscar_cliente_completo(self.cliente['id'])
            if dados and dados.get('trainer_editou'):
                self.treinos = dados['treinos']
                self.treinos_nomes = dados['treinos_nomes']
                with open(self.treinos_file, 'w', encoding='utf-8') as f:
                    json.dump(self.treinos, f, ensure_ascii=False)
                Clock.schedule_once(lambda dt: self.sm.get_screen('home')._reconstruir_botoes() if self.sm.has_screen('home') else None)
        except: pass

    def _verificar_sync_diario(self, _dt):
        pass

if __name__ == '__main__':
    try:
        RonaldoMedeirosFisiologistaApp().run()
    except Exception as e:
        print(f"CRASH FATAL: {e}")
