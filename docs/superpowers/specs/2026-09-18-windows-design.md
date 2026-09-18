# O e-Disciplinas em Windows — design

> 18/09/2026. Este documento faz duas coisas, e é importante não confundi-las:
> **implementa** o caminho barato e reversível (manter o `token.sh` em bash e
> acrescentar o que Windows precisa), e **apresenta com custo medido** o caminho
> caro (reescrever o `token.sh` em Python) para o dono decidir depois, com dado.
> A segunda decisão **não foi tomada aqui**, de propósito.
>
> Tudo o que este spec diz sobre Windows foi escrito **num Mac, sem Windows à
> mão**. O que está provado é o que a suíte alcança: a *escolha* da ferramenta
> conforme o que existe no PATH. O que a ferramenta faz num Windows real está
> listado no §6 como pendente, com o que conferir.

- **Prioridade:** alta — o dono viveu o defeito ao instalar em Windows em 17/09
- **Arquivos:** `scripts/token.sh`, `tests/moodle/test_token_windows.py` (novo),
  `README.md`, `docs/agents/CONVENTIONS.md`, `docs/decisions/BACKLOG-correcoes.md`
- **Não tocados, de propósito:** `usp_mcp/`, `SPEC1.md`, `capacidades.py`, os
  outros nove scripts de `scripts/`

## 1. Sintoma e causa

O dono tentou instalar em Windows e a vigia do clipboard do `token.sh` não
funcionou. A causa está no próprio script, e não precisa de Windows para ser
lida:

| o script escolhia entre | Windows tem | consequência |
|---|---|---|
| `pbpaste`, `wl-paste`, `xclip` (leitor de clipboard) | nenhum | sem leitor, o script diz "não há clipboard para vigiar" e cai no fluxo em duas invocações — cujo segundo comando também era `pbpaste \|` |
| `open`, `xdg-open` (lançador do navegador) | nenhum | a página não abre; a URL fica impressa para abrir à mão |
| `.venv/bin/python`, senão `python3` | `.venv/Scripts/python.exe`; `python3` pode não existir | o script pode nem chegar ao passo 1 |

O resto do projeto não tem esse problema. Medido antes desta tarefa, e não
reconferido aqui: `usp_mcp/` não supõe sistema operacional nenhum, os três
servidores são Python puro, e o depósito usa `Path.home() / ".cache"`, que existe
em Windows. **Em Windows, bandejão e JupiterWeb funcionam em tese; o e-Disciplinas
não, porque a única forma de obter a chave é o `token.sh`, e ele não rodava.**

## 2. As duas opções, com o custo que dá para medir daqui

### (a) Manter o bash e acrescentar o que falta — **implementada**

A cada uma das três escolhas do script, acrescentar o candidato que Windows tem,
**sem mudar a ordem do que já existia** e sempre como último recurso:

- leitor: `powershell.exe` / `powershell` / `pwsh.exe` / `pwsh`, com
  `-NoProfile -Command Get-Clipboard`, e `tr -d '\r'` no fim (o Get-Clipboard
  termina em CRLF);
- lançador: `wslview` antes de tudo (só existe no WSL; ver §4), `rundll32
  url.dll,FileProtocolHandler <url>` por último;
- Python: `.venv/Scripts/python.exe` depois de `.venv/bin/python`; `python`
  depois de `python3`; e uma falha legível se não houver nenhum.

Mais o README dizendo o que muda no Windows e o que não foi conferido.

**Custo medido:** cerca de 70 linhas no `token.sh` (dos quais a maior parte é
comentário dizendo o porquê de cada posição), 17 testes novos numa família própria
(`WIN1-WIN7`), uma subseção no README. Uma sessão. **Reversível:** nada do que
existia mudou de forma, e os 58 testes que já exercitavam o script passam sem
uma linha alterada.

**O que (a) não resolve:** a pessoa precisa de bash. Em Windows isso é Git Bash
(vem com o Git para Windows) ou WSL. Para o público do README, que "não precisa
saber programar", abrir o Git Bash e rodar `bash ~/usp-mcp/scripts/token.sh` é
um degrau a mais. E os outros nove scripts de `scripts/` continuam assumindo
`.venv/bin/python` — o `gate.sh` inclusive, o que faz o "caminho rápido" do README
falhar no passo 1 em Windows. Isso é de quem mantém, não de quem usa, e ficou
fora.

### (b) Reescrever o `token.sh` em Python — **não implementada**

Um `scripts/token.py` que a pessoa roda do PowerShell, sem bash. Clipboard por
`ctypes` (user32) ou por `subprocess` do PowerShell, navegador pelo módulo
`webbrowser` da biblioteca padrão, caminhos por `pathlib`. Resolve Windows, Mac e
Linux de uma vez e elimina a dependência de bash de quem usa.

**Custo medido do que seria jogado fora ou reconstruído:**

| o quê | tamanho | observação |
|---|---|---|
| `scripts/token.sh` | 744 linhas antes desta tarefa | ~14 medições datadas nos comentários (10/09 a 17/09), sete passos com invariantes próprios |
| linhas de mensagem (`nota`/`aviso`) | 122 | são o texto que a pessoa lê, e é sobre elas que os testes afirmam |
| testes que executam o script | 58 (em `test_token_navegador.py`, `test_token_decode.py`, `test_token_fora_do_argv.py`) | todos fazem `subprocess.run(["bash", "scripts/token.sh"])` ou `pty.fork` + `execve(bash)`, e afirmam sobre frases exatas |
| dublês no PATH | `open`, `pbpaste`, `curl` | continuariam valendo se o Python chamasse os mesmos comandos; não valeriam para `ctypes`/`webbrowser` |

Ou se mantém a mesma interface (stdin, códigos de saída 0/1/2/3, as mesmas
frases) para os 58 testes continuarem valendo — e aí a reescrita é uma
transliteração linha a linha, com pouco ganho de desenho —, ou se reescreve a
suíte junto. Estimativa honesta: duas a três sessões, e um período em que dois
obtentores de token coexistem.

**O que (b) não resolve sozinha:** o `.env` gravado com `\n` que o Bloco de Notas
converte em CRLF, o `.venv/Scripts` nos outros scripts, e o fato de que ninguém
testou em Windows. A última é a mesma para as duas opções.

## 3. Por que (a) agora, e o que faria (b) valer a pena

(a) destrava o e-Disciplinas em Windows hoje, para quem tem Git Bash, sem
apostar nada: se um Windows real mostrar que o caminho por bash não serve, o
custo afundado é uma sessão e o desenho de (b) sai daqui com o que o testador
relatou.

O dado que decide (b) é um destes três, vindo de alguém com Windows:

1. **Atrito de instalação.** Se "instale o Git para Windows, abra o Git Bash"
   for o passo em que as pessoas param, (b) vale: o script em Python roda do
   PowerShell que a pessoa já abriu para o `python -m venv`.
2. **O MSYS não engole o caminho que o Python devolve.** `achar_env()` devolve
   `C:\Users\...\.env`. O bash do Git Bash costuma aceitar caminhos Win32, mas
   `dirname` não os entende (devolve `.`), então `.cache/` cai no diretório
   corrente — que é a raiz do clone, o mesmo lugar, na instalação do README.
   Se o passo 1 falhar ao fazer `. "$ENV_FILE"`, (a) não fecha sem gambiarra
   (`cygpath`), e (b) fecha de graça.
3. **O arranque do PowerShell.** A vigia lê a cada 0,5 s e conta 2 leituras por
   segundo; cada leitura por `powershell -NoProfile -Command Get-Clipboard`
   custa um processo novo, e o arranque do Windows PowerShell 5.1 é da ordem de
   segundos em máquina fria (não medido por mim). Se for ~1 s, a vigia de 90 s
   dura ~4,5 min de relógio e estoura o teto de 120 s por chamada de um agente
   (regra 3 da vigia). Cura em (a): laço por relógio, ou padrão menor de
   `USP_MCP_VIGIA_SEGUNDOS` quando o leitor é PowerShell. Cura em (b): ler o
   clipboard por `ctypes`, sem processo.

Se nenhum dos três aparecer, (a) basta e (b) é gasto.

## 4. Decisões de desenho dentro de (a)

**O PowerShell é o último leitor, não o primeiro.** Num Mac com `pwsh` instalado
por acaso, o leitor continua sendo o `pbpaste` (WIN3). Acrescentar sem reordenar
é o que mantém os 58 testes intactos.

**`wslview` é o primeiro lançador, e isso é uma mudança de ordem.** É a única
posição que funciona: no Ubuntu do WSL, `/usr/bin/open` é o `openvt` do pacote
`kbd` — `command -v open` acha, o script chamaria `openvt URL`, e falharia. E com
o WSLg, `xdg-open` abriria um navegador *Linux*, que não está logado na Senha
Única. `wslview` abre o navegador do Windows, que é onde a pessoa está logada. Só
existe no WSL, então em Mac e Linux puro a ordem efetiva não muda (WIN6c, WIN6d).
O `open`→`openvt` em Linux sem WSL é um achado colateral, registrado no BACKLOG.

**`rundll32`, e não `cmd /c start` nem `explorer.exe` nem `Start-Process`.** A
URL do `launch.php` tem `&`. Pelo `cmd.exe`, `&` é separador de comando e a URL
chega cortada, salvo com aspas que o MSYS não garante pôr. `explorer.exe URL`
abre o navegador mas devolve código 1 mesmo quando dá certo (quirk conhecido), e
o script reportaria "falhou". `powershell Start-Process` exige a URL entre
aspas simples *dentro* de uma string que já passa por duas camadas de aspas.
`rundll32 url.dll,FileProtocolHandler URL` recebe a URL como argumento, sem
interpretação no meio, e é o ShellExecute do Windows: o mesmo que um clique
duplo faz. É o de menos camadas para defender às cegas. Se falhar, o script já
diz "abra a URL acima à mão" — a URL está impressa.

**`.exe` antes do nome sem extensão.** No WSL o Linux não completa `.exe`; no
Git Bash o MSYS completa. Os dois nomes valem (WIN2, WIN6b).

**`-NoProfile`.** O perfil da pessoa é o que mais custa no arranque do
PowerShell, e a vigia arranca um por leitura. Nenhum outro parâmetro: quanto
menos eu afirmo sobre uma ferramenta que não rodei, menos tenho a corrigir.

## 5. O que a suíte prova (WIN1-WIN7)

Todos com dublês no PATH, em pastas próprias para controlar exatamente o que
existe em cada cenário; nenhum lê o clipboard real da máquina (há uma pessoa
usando-a), nenhum abre navegador, nenhum toca a rede. O "PowerShell" dublado é o
mesmo roteiro do `pbpaste` dublado atrás de outro nome, e o que se afirma é o
**argumento enviado** (regra 11 do `CLAUDE.md`), não a saída.

| # | prova |
|---|---|
| WIN1 | sem os três leitores e com `powershell.exe`: a vigia se anuncia citando-o, chama-o com `-NoProfile -Command Get-Clipboard` a cada leitura, e segue até gravar |
| WIN2 | os quatro nomes, cada um sozinho, são escolhidos e chamados com o mesmo argv |
| WIN3 | com `pbpaste` no PATH, o PowerShell não é chamado nem uma vez |
| WIN4 | CRLF no fim do endereço não estraga a forma nem a conferência do passaporte, e não vai para o `.env` |
| WIN5 | a saída 3 ensina o comando do Windows junto do `pbpaste \|`; a máquina sem leitor nomeia o PowerShell entre os que faltam |
| WIN6 | `rundll32` recebe `url.dll,FileProtocolHandler <url>`; `wslview` recebe a URL e vence o `open`; `open` vence o `rundll32`; a máquina sem lançador nomeia os do Windows |
| WIN7 | `.venv/Scripts/python.exe` serve sem `.venv/bin/python`; `python` serve sem `python3`; sem nenhum, falha legível antes do passo 1 |

Os 58 testes anteriores passam sem alteração.

## 6. O que NÃO está provado, e o que alguém com Windows deve conferir

Em ordem do que mais provavelmente morde:

1. **Passo 1 no Git Bash.** `achar_env()` devolve `C:\Users\...\.env`. Conferir
   que o script imprime esse caminho, faz `. "$ENV_FILE"` sem erro e mostra
   `MOODLE_URL`. Se falhar aqui, é o item 2 do §3.
2. **Tempo de `powershell -NoProfile -Command Get-Clipboard`.** Medir com
   `time`. Acima de ~0,5 s, a vigia de 90 s passa do teto de um agente (item 3
   do §3).
3. **`rundll32 url.dll,FileProtocolHandler <url>` abre o navegador padrão** com
   a URL inteira (o `&passport=` chegou?), e o script diz "abri a URL" e não
   "ainda não voltou depois de 2 s".
4. **A vigia de ponta a ponta:** copiar o endereço do link no navegador do
   Windows e ver o script seguir sozinho até `7/7  grava no .env`.
5. **O fluxo em duas invocações:** `powershell -NoProfile -Command Get-Clipboard
   | bash scripts/token.sh` grava.
6. **WSL:** `wslview` abre o navegador do Windows; `powershell.exe` lê o clipboard
   do Windows; nenhum aviso de UNC na saída.
7. **Permissão do passaporte.** `umask 077` não faz nada em NTFS; o arquivo não
   fica 0600. Não é segredo (vai na URL), então isso é registro, não defeito.
8. **`.env` com CRLF.** Quem abrir o `.env` no Bloco de Notas e salvar pode
   trocar as quebras de linha; o bash leria `MOODLE_URL=...\r`. Vale para os
   servidores também (`usp_mcp/env.py`), e não é deste spec.

O relato desses oito pontos é o dado que fecha (a) como suficiente ou abre (b).
Até ele chegar, o README diz "em teoria; ninguém conferiu" — e é para dizer.

## 7. O que ficou de fora, de propósito

- **Os outros nove scripts de `scripts/`** (`gate.sh`, `ws.sh`, `servidor.sh`,
  `userid.sh`, `fix-token.sh`, `capture.sh`, `compatibilidade.sh`,
  `_capturar_redirect.sh`, mais os `.py`) continuam com `.venv/bin/python`. São
  de manutenção; quem usa não os roda. O `gate.sh` no "caminho rápido" do README
  é a exceção, e o README agora avisa.
- **`--auto`** (`_capturar_redirect.sh`) é macOS por construção (`osacompile`) e
  nunca entregou contra a USP; não faz sentido portar.
- **Detectar Windows por `uname`** para mudar mensagens ou padrões. A detecção
  por *ferramenta presente* é a que o script já usava, e é a que não mente num
  WSL com `wl-paste` instalado.
- **`/dev/clipboard`** do MSYS. Existe no Cygwin; não sei se no Git Bash. Sem
  medir, não entra.
- **CHANGELOG.** A 1.1.0 saiu hoje; a linha do Windows entra na próxima versão,
  com o que o testador relatar, em vez de prometer agora o que não foi visto.
