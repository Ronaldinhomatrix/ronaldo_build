import json
import os
import platform
import threading
import uuid
from datetime import datetime

# 1. Configurações de Ambiente (Devem ser as primeiras)
os.environ['KIVY_VIDEO'] = 'ffpyplayer'
if platform.system() == 'Windows':
    os.environ['KIVY_GL_BACKEND'] = 'angle_sdl2'

# 2. Imports do Kivy (Protegidos)
try:
    from kivy.clock import Clock
    from kivy.core.text import LabelBase
    from kivy.uix.screenmanager import ScreenManager, SlideTransition
    from kivymd.app import MDApp
except Exception as e:
    print(f"Erro nos imports básicos: {e}")

# 3. Import do Firebase (Pode causar crash se SSL falhar)
try:
    import firebase_sync
except Exception as e:
    print(f"Erro ao importar Firebase: {e}")

def _pasta_downloads():
    if platform.system() == 'Android':
        return '/storage/emulated/0/Download'
    return os.path.join(os.path.expanduser('~'), 'Downloads')

class RonaldoMedeirosFisiologistaApp(MDApp):
    def build(self):
        try:
            self.title = 'Ronaldo Medeiros Fisiologista'
            self.theme_cls.primary_palette = 'BlueGray'
            self.theme_cls.theme_style = 'Dark'

            # Pasta de dados segura para Android
            self.data_dir = self.user_data_dir
            os.makedirs(self.data_dir, exist_ok=True)
            
            # Caminhos dos arquivos
            self.treinos_file       = os.path.join(self.data_dir, 'treinos.json')
            self.treinos_nomes_file = os.path.join(self.data_dir, 'treinos_nomes.json')
            self.historico_file     = os.path.join(self.data_dir, 'historico.json')
            self.atividade_file     = os.path.join(self.data_dir, 'historico_atividade.json')
            self.cliente_file       = os.path.join(self.data_dir, 'cliente.json')
            self.sync_file          = os.path.join(self.data_dir, 'ultima_sync.json')
            self._CLIENTE_BACKUP    = os.path.join(_pasta_downloads(), 'ronaldo_cliente_backup.json')

            # Registro de Fonte (Protegido contra case-sensitivity)
            try:
                # Tenta vários caminhos possíveis para a fonte
                fontes_possiveis = [
                    os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'ERASBD.TTF'),
                    os.path.join(os.path.dirname(__file__), 'assets', 'fonts', 'erasbd.ttf'),
                    'assets/fonts/ERASBD.TTF'
                ]
                for p in fontes_possiveis:
                    if os.path.exists(p):
                        LabelBase.register(name='ErasBoldITC', fn_regular=p)
                        break
            except: pass

            self.pode_editar      = True
            self.treino_atual     = ''
            self.progresso_treino = {}
            
            # Carregamento resiliente
            self.cliente       = self._carregar(self.cliente_file, None) or self._recuperar_cliente_downloads()
            self.treinos       = self._carregar(self.treinos_file,       {})
            self.treinos_nomes = self._carregar(self.treinos_nomes_file, {})
            self.historico     = self._carregar(self.historico_file,     {})
            self.atividade     = self._carregar(self.atividade_file,     [])

            # Import das telas (Dentro do build para evitar crash no loading)
            from telas.tela_cadastro import TelaCadastro
            from telas.tela_home import TelaHome
            from telas.tela_treino import TelaTreino
            from telas.tela_historico import TelaHistorico
            from telas.tela_atividade import TelaAtividade
            from telas.tela_download import TelaDownload

            self.sm = ScreenManager(transition=SlideTransition())
            self.sm.add_widget(TelaDownload(name='download'))
            self.sm.add_widget(TelaCadastro(name='cadastro'))
            self.sm.add_widget(TelaHome(name='home'))
            self.sm.add_widget(TelaTreino(name='treino'))
            self.sm.add_widget(TelaHistorico(name='historico'))
            self.sm.add_widget(TelaAtividade(name='atividade'))

            # Verificação de vídeos sem travar
            videos_ok = False
            try:
                flag = os.path.join(self.data_dir, 'videos_ok.flag')
                videos_ok = os.path.exists(flag)
            except: pass

            if not videos_ok:
                self.sm.current = 'download'
            elif self.cliente:
                self.sm.current = 'home'
            else:
                self.sm.current = 'cadastro'
                
            return self.sm
        except Exception as e:
            print(f"ERRO CRÍTICO NO BUILD: {e}")
            # Retorna uma tela de erro básica em vez de fechar
            from kivy.uix.label import Label
            return Label(text=f"Erro ao iniciar:\n{str(e)}")

    def on_start(self):
        if self.cliente:
            threading.Thread(target=self._puxar_treinos_firebase, daemon=True).start()

    def _carregar(self, path, default):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return default

    def _recuperar_cliente_downloads(self):
        try:
            dados = self._carregar(self._CLIENTE_BACKUP, None)
            if dados and dados.get('id'):
                cliente = {'id': dados['id'], 'nome': dados['nome']}
                with open(self.cliente_file, 'w', encoding='utf-8') as f:
                    json.dump(cliente, f)
                return cliente
        except: pass
        return None

    def salvar(self, **kwargs):
        # Simplificado para evitar crash em threads
        threading.Thread(target=self._executar_salvamento, kwargs=kwargs, daemon=True).start()

    def _executar_salvamento(self, **kwargs):
        try:
            with open(self.treinos_file, 'w', encoding='utf-8') as f:
                json.dump(self.treinos, f)
            if self.cliente:
                firebase_sync.salvar_dados(self.cliente['id'], self.historico, self.atividade)
        except: pass

    def _puxar_treinos_firebase(self):
        try:
            dados = firebase_sync.buscar_cliente_completo(self.cliente['id'])
            if dados and dados.get('trainer_editou'):
                self.treinos = dados['treinos']
                with open(self.treinos_file, 'w', encoding='utf-8') as f:
                    json.dump(self.treinos, f)
                Clock.schedule_once(lambda dt: self.sm.get_screen('home')._reconstruir_botoes() if self.sm.has_screen('home') else None)
        except: pass

if __name__ == '__main__':
    RonaldoMedeirosFisiologistaApp().run()
