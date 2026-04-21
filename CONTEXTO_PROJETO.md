# Contexto do Projeto — Ronaldo Medeiros Fisiologista

> Este documento é para leitura por IA assistente (Gemini, Claude, etc.).
> Contém tudo que é necessário para entender e continuar o desenvolvimento do projeto.

---

## 1. O que é este projeto

App Android para personal trainer. O **treinador** (Ronaldo Medeiros) gerencia clientes
via painel web; cada **cliente** usa o app no celular para ver e registrar treinos.

- **App mobile**: Python + Kivy/KivyMD, compilado com buildozer para Android APK
- **Painel web**: Flask + Firebase Admin, hospedado no Render
- **Backend**: Firebase Firestore (sync entre app e painel)
- **Distribuição**: APK direto (não está na Play Store)

---

## 2. Stack tecnológico

| Camada | Tecnologia |
|--------|-----------|
| App mobile | Python 3, Kivy 2.3.0, KivyMD 1.2.0 |
| Compilação Android | buildozer + python-for-android (p4a), WSL Ubuntu |
| Backend | Firebase Firestore (REST API, não SDK oficial) |
| Painel web | Flask, hospedado no Render |
| Vídeos | ffpyplayer; hospedados no GitHub público |
| Fonte customizada | Eras Bold ITC (`assets/fonts/ERASBD.TTF`) |

**Importante:** este não é um projeto Android nativo (Kotlin/Java).
É Python compilado para Android via buildozer. Editar `.py` e rebuildar gera o APK.

---

## 3. Estrutura de arquivos

```
ronaldo_build/
├── main.py                    # Ponto de entrada do app; carrega telas e dados
├── buildozer.spec             # Configuração do build Android (versão, permissões, keystore)
├── build_android.sh           # Script de build — rodar no WSL Ubuntu
├── firebase_sync.py           # Sync com Firebase Firestore (leitura/escrita)
├── firebase_config.py         # Credenciais do Firebase (API_KEY, PROJECT_ID, etc.) — NÃO commitar segredos
├── icon_rm.png                # Ícone do app
│
├── assets/
│   ├── fonts/ERASBD.TTF       # Fonte Eras Bold ITC
│   └── images/
│       ├── foto_perfil.jpg    # Foto circular do treinador (tela home)
│       └── Logo_Marca.jpg     # Logo OperantLab (tela Sobre)
│
├── data/                      # Dados locais do cliente (gerados em runtime, não versionar)
│   ├── cliente.json           # ID e nome do cliente
│   ├── treinos.json           # Plano de treino atual
│   ├── treinos_nomes.json     # Nomes personalizados dos treinos (ex: "Peito e Tríceps")
│   ├── historico.json         # Histórico de peso por exercício
│   └── historico_atividade.json # Registro de séries concluídas
│
├── telas/
│   ├── tela_cadastro.py       # Primeira execução: cadastro do cliente
│   ├── tela_home.py           # Tela principal: foto, botões de treino A/B/C/D/E
│   ├── tela_treino.py         # Lista de exercícios do treino selecionado
│   ├── tela_historico.py      # Histórico de sessões
│   ├── tela_atividade.py      # Atividade recente (séries marcadas)
│   ├── tela_configuracoes.py  # Tela "Sobre" com logo e email
│   └── tela_download.py       # Download dos vídeos na 1ª abertura
│
└── painel/                    # Painel web Flask (deploy no Render, independente do app)
    ├── app.py                 # Servidor Flask principal
    └── templates/             # HTML do painel
```

---

## 4. Como buildar o APK

**Requisito:** WSL Ubuntu instalado no Windows com o projeto em `/mnt/c/Users/madm/ronaldo_build`.

```bash
# No terminal WSL:
bash /mnt/c/Users/madm/ronaldo_build/build_android.sh
```

O script faz automaticamente:
1. Copia o projeto para `~/ronaldo_build` (filesystem Linux, mais rápido)
2. Instala dependências do sistema (apt) e buildozer/cython
3. Cria a keystore de assinatura em `/mnt/c/Users/madm/keystore/ronaldo.jks` (apenas na 1ª vez)
4. Compila com `buildozer android release`
5. Assina o APK com `zipalign` + `apksigner`
6. Copia o APK final para `C:\Users\madm\ronaldo_build\Instalador\RonaldoMedeirosFisiologista_v2.8.apk`

**Tempo de build:**
- 1ª build (sem cache): 30–60 min
- Builds subsequentes: 2–5 min

**Versão atual:** 2.8 (definida em `buildozer.spec` → `version = 2.8`)

**Keystore (assinatura):**
- Arquivo: `C:\Users\madm\keystore\ronaldo.jks`
- Senha: `RonFisio@2024!Mdf`
- **Guardar esta senha com segurança** — necessária para toda atualização futura do app

---

## 4.1. Fluxo de Atualização (Deploy)

Para que as alterações no código reflitam no servidor (Render) e no Telegram:

1. **Configurar Identidade (Apenas uma vez no PC):**
   ```powershell
   git config --global user.email "seu-email@exemplo.com"
   git config --global user.name "Ronaldo Medeiros"
   ```

2. **Enviar para o GitHub/Render:**
   No Terminal do Windows (PowerShell):
   ```powershell
   git add .
   git commit -m "Descricao da mudanca (ex: Correcao de cores)"
   git push
   ```
   *O Render detectará o push e atualizará o serviço automaticamente em ~5 min.*

3. **Gerar Novo APK:**
   No Terminal WSL (Ubuntu):
   ```bash
   bash /mnt/c/ronaldo_build/build_android.sh
   ```

---

## 5. Como o Firebase funciona no app

O app NÃO usa o SDK oficial do Firebase. Usa a REST API do Firestore diretamente via `requests`.

### Arquivos relevantes

- `firebase_config.py` — contém `API_KEY`, `PROJECT_ID`, `PAINEL_URL`, `NOTIF_TOKEN`
- `firebase_sync.py` — todas as funções de leitura/escrita no Firestore

### Coleções no Firestore

| Coleção | Conteúdo |
|---------|---------|
| `atletas` | Documentos de cada cliente (treinos, histórico, atividade, obs) |
| `exercicios` | Banco de exercícios disponíveis |
| `banco_treinos` | Templates de treino do treinador |

### Campos por cliente (`atletas/{cliente_id}`)

```
nome, treinos, treinos_nomes, historico, atividade, obs_cliente,
trainer_editou, pode_editar, treino_atual, data_admissao
```

### Fluxo de sync

- **Treinador edita treino no painel** → `trainer_editou = true` no Firestore
- **App abre / volta ao 1º plano** → verifica `trainer_editou`; se true, baixa novos treinos
- **Cliente marca série** → app envia `atividade` ao Firestore (retry offline)
- **Cliente finaliza treino** → app envia `historico + atividade + obs`

---

## 6. Estrutura de dados — exercício

```json
{
  "id": "uuid-gerado-automaticamente",
  "nome": "Supino Reto",
  "series": "4",
  "repeticoes": "12",
  "peso": "80kg"
}
```

**Atenção:** exercícios antigos podem não ter o campo `repeticoes`.
O `CardExercicio` em `tela_treino.py` tem fallback para esse caso.

---

## 7. Telas — guia rápido

### tela_home.py
- Foto circular do treinador + botões dos treinos (A/B/C/D/E)
- Botão do treino atual fica verde (definido pelo treinador via painel)
- Tudo dentro de `ScrollView` para funcionar em celulares com muitos treinos
- Rodapé fixo: Histórico | Sincronizar | Sobre

### tela_treino.py
- Lista de exercícios do treino selecionado
- Cada exercício é um `CardExercicio` com 4 linhas:
  1. Nome (azul, fundo escuro)
  2. Séries + Peso
  3. Repetições
  4. Botões "Adicionar Observação" e "Feito"
- Botão "Feito" fica verde quando marcado; "Adicionar Observação" fica amarelo se tem obs
- "Registrar treino completo" salva e sincroniza com Firebase

### tela_cadastro.py
- Exibida na 1ª execução (sem `data/cliente.json`)
- Cria o cliente no Firestore via `firebase_sync.criar_cliente()`
- Ao cadastrar: zera treinos/histórico locais + salva backup em Downloads

### tela_download.py
- Exibida se os vídeos ainda não foram baixados
- Baixa 52 vídeos MP4 do repositório GitHub público
- URL base: `https://raw.githubusercontent.com/marcosalexandredemedeiros-glitch/ronaldo-medeiros-fisiologista-videos/main/videos/`
- Salva em `app.user_data_dir/videos/` no celular
- Cria flag `videos_ok.flag` ao concluir

---

## 8. Sizing dinâmico — regras obrigatórias

| O que | Como | Por quê |
|-------|------|---------|
| Fontes (labels, botões) | `'16sp'`, `'13sp'` etc. | Adapta densidade + preferência do usuário |
| Alturas de linhas/cards | `Window.height * 0.055` | Adapta ao tamanho físico da tela |
| Larguras de botões | `Window.width * 0.320` | Idem |
| Espaçamentos | `Window.height * 0.008` | Idem |

**Nunca usar `Window.width * fator` como `font_size`** — causa tamanhos inconsistentes.

---

## 9. Tarefas comuns

### Mudar versão do app
1. `buildozer.spec` → linha `version = 2.8` → incrementar
2. `build_android.sh` → linha `cp "$SIGNED" ... v2.8.apk"` → atualizar nome do arquivo

### Adicionar um campo novo ao exercício (ex: "observação do treinador")
1. No painel (`painel/app.py`): adicionar o campo ao formulário e salvar no Firestore
2. No app (`tela_treino.py`): no `CardExercicio`, adicionar linha para exibir o campo
3. Em `firebase_sync.py`: garantir que o campo seja lido em `buscar_cliente_completo()`

### Mudar a foto do treinador
1. Substituir `assets/images/foto_perfil.jpg` (JPEG, imagem quadrada, mínimo 400×400px)
2. Rebuildar o APK

### Mudar cores do tema
- `main.py` → `self.theme_cls.primary_palette = 'Blue'` (trocar 'Blue' por outra cor KivyMD)
- Cor de destaque azul `#5b9cf6` usada diretamente em vários widgets em `tela_treino.py`

### Adicionar nova tela
1. Criar `telas/tela_nova.py` herdando de `MDScreen`
2. Em `main.py`: importar e adicionar `self.sm.add_widget(TelaNova(name='nova'))`
3. Navegar: `MDApp.get_running_app().sm.current = 'nova'`

### Alterar texto da tela "Sobre"
- `telas/tela_configuracoes.py` — editar os labels e o email exibido

---

## 10. Variáveis de ambiente — painel web (Render)

O painel web roda no Render e precisa destas variáveis de ambiente configuradas lá:

| Variável | Descrição |
|----------|-----------|
| `FIREBASE_SA_JSON` | JSON completo do serviceAccount do Firebase |
| `PAINEL_SENHA` | Senha de acesso ao painel web |
| `SECRET_KEY` | Chave de sessão Flask (string aleatória) |
| `TELEGRAM_TOKEN` | Token do bot Telegram (notificações de obs) |
| `TELEGRAM_CHAT_ID` | `6476935180` (chat do Ronaldo) |
| `NOTIF_TOKEN` | Token compartilhado app↔painel (mesmo valor em `firebase_config.py`) |

---

## 11. Repositórios GitHub

| Repo | Visibilidade | Conteúdo |
|------|-------------|---------|
| `marcosalexandredemedeiros-glitch/ronaldo-medeiros-fisiologista` | Privado | Código-fonte do app e painel |
| `marcosalexandredemedeiros-glitch/ronaldo-medeiros-fisiologista-videos` | Público | 52 vídeos MP4 + release do APK |

**Link de download do APK (v2.8):**
```
https://github.com/marcosalexandredemedeiros-glitch/ronaldo-medeiros-fisiologista-videos/releases/download/v2.8/RonaldoMedeirosFisiologista_v2.8.apk
```

---

## 12. O que NÃO mexer

- `firebase_config.py` — não alterar os valores sem atualizar o Firebase e o painel
- Coleção `atletas` no Firestore — não renomear (quebraria dados de clientes existentes)
- A keystore em `C:\Users\madm\keystore\ronaldo.jks` — não apagar; sem ela não é possível atualizar o app nos celulares dos clientes
- `source.exclude_dirs` no `buildozer.spec` — garante que pastas desnecessárias não entrem no APK

---

## 13. Diagnóstico de crash no Android

```bash
# 1. Limpar log
adb -s RQCTA06LENV logcat -c

# 2. Abrir o app no celular

# 3. Capturar log
adb -s RQCTA06LENV logcat -d > logcat.txt

# 4. Ler (arquivo pode ser UTF-16)
python -c "
import codecs
with codecs.open('logcat.txt', 'r', 'utf-16') as f:
    for line in f:
        if 'python' in line.lower() or 'error' in line.lower():
            print(line, end='')
"
```

Procurar a linha `Start proc NNN:com.operantlab.ronaldomedeirosfisiologista` para pegar o PID,
depois filtrar as linhas com esse PID e tag `python`.

---

## 14. Observações para a IA assistente

- Todos os arquivos relevantes do app estão em `telas/` e `main.py`
- `firebase_sync.py` é o ponto central de comunicação com o backend
- O app usa `MDApp.get_running_app()` para acessar dados globais (treinos, cliente, etc.)
- Sizing: sempre usar `sp` para fontes e `Window.height/width * fator` para dimensões físicas
- Não usar `size_hint` relativo dentro de `ScrollView` — usar tamanhos fixos em `dp` ou `Window.*`
- O tema KivyMD sobrescreve `font_size` em `MDLabel`; para controle preciso usar `Label` puro do Kivy
- Após qualquer mudança em `.py`, é necessário rebuildar o APK via `build_android.sh`
