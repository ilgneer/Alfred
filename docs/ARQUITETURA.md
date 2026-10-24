# Arquitetura

## Visão geral

```
                ┌──────────────── platform ────────────────┐
 Explorer ──►   │ gesture.py  (Shift+arrastar, sem hooks)  │
 menu/Enviar ─► │ single_instance.py (canal local + mutex) │──┐
                │ integration.py (HKCU), win32.py (ctypes) │  │
                └──────────────────────────────────────────┘  │
                ┌──────────────────── ui ───────────────────┐  │      ┌────────────── core ───────────────┐
                │ radial.py  RadialMenu + CatchOverlay      │◄─┼──────│ routes.py   registro de conversões │
                │ main_window.py + pages/                   │  │      │ engines.py  detecção dos motores   │
                │ toast.py, tray.py, sounds.py, icons.py    │  │      │ jobs.py     fila + cancelamento    │
                └──────────────────────────────────────────┘  │      │ context.py  staging/sem sobrescrita│
                                app.py (controlador) ◄─────────┘      │ converters/ imagens, mídia, PDF… │
                                                                      └───────────────────────────────────┘
```

- `core` não importa nada de interface: é testado isoladamente e reutilizado pelo autoteste.
- `routes.py` é a **fonte única de verdade**: a roda, a matriz de compatibilidade e os testes leem dele.
  Uma rota só aparece na roda se todos os motores do seu *plano* estiverem disponíveis nesta máquina.
- Cada rota pode ter planos alternativos (ex.: DOCX → PDF via LibreOffice; sem ele, via Pandoc + Qt,
  marcado como experimental).

## O gesto Shift + arrastar

Problema do v1: a roda aparecia *durante* um arrasto que o Windows trata como **mover** (Shift).
Soltar fora da área desenhada fazia o Explorer mover o arquivo de verdade. Além disso, a seleção era
lida por um PowerShell (até 6 s de atraso) e o gesto disparava em qualquer programa.

Solução do v2:

1. `GestureMonitor` amostra o estado do mouse/teclado a cada 25 ms com `GetAsyncKeyState`.
   **Não há hook global**: o Alfred nunca atrasa o mouse ou o teclado do usuário, mesmo ocupado.
2. O gesto só “arma” se o botão foi pressionado **sobre uma janela do `explorer.exe`** (pastas ou área
   de trabalho), com o modificador configurado e após 12 px de movimento.
3. Armar apenas mostra o `CatchOverlay`: uma janela invisível (1,5 % de opacidade) do tamanho do
   monitor, registrada como alvo OLE de arrastar-e-soltar.
4. Quando o arrasto **real** do Windows entra no overlay com arquivos (`CF_HDROP`), a roda abre
   centralizada no cursor. Assim, uma seleção por retângulo (Shift + arrastar no vazio) nunca abre a
   roda, e os arquivos vêm do próprio arrasto — exatamente os que o usuário está segurando.
5. A roda também é um **alvo OLE**. Passar sobre um segmento destaca o formato; **soltar escolhe**.
   O efeito devolvido ao Explorer é sempre **COPIAR** (nunca mover), então a origem não apaga nada.
6. Soltar no overlay (fora da roda) é recusado (`DROPEFFECT_NONE`): o Explorer não recebe o drop e
   nada acontece com o arquivo — cancelamento seguro. Soltar no centro “fixa” a roda para escolher com
   clique ou teclado.
7. **Esc**: o próprio laço OLE do Explorer cancela o arrasto, e o monitor detecta a tecla e fecha a roda
   imediatamente (funciona mesmo sem foco de teclado).

Limitações conhecidas (documentadas e com alternativas):

- Com “Shift + arrastar” ativo, Shift deixa de **mover** arquivos no Explorer enquanto o Alfred roda.
  Alternativas: outro modificador (Shift+Ctrl / Shift+Alt) ou desativar pela bandeja.
- O overlay cobre o monitor onde o gesto começou. Soltar em **outro** monitor segue o comportamento
  normal do Windows.
- Itens virtuais (dentro de um ZIP aberto no Explorer, celulares MTP) não têm caminho de arquivo e
  não abrem a roda.
- Se o Alfred estiver rodando como **administrador**, o Windows bloqueia o arrastar vindo do Explorer
  (UIPI). O instalador nunca eleva o app.
- No Windows 11, o item do menu de contexto aparece em “Mostrar mais opções” (o menu novo exige um
  pacote MSIX com extensão COM — fora do escopo desta versão).

## Janelas sem fundo quadrado

`RadialMenu` usa `WA_TranslucentBackground` + `FramelessWindowHint` + `Tool`: o Windows cria uma janela
*layered* com alfa por pixel. Só o círculo é pintado; os cantos têm alfa 0 (teste automatizado verifica).
Pixels com alfa 0 também são transparentes para o clique e para o arrastar, que caem no overlay.

## Conversões seguras

`ConvertContext` grava tudo numa pasta oculta `.alfred-xxxx` **dentro da pasta de destino** (mesmo
volume). Só depois do sucesso os arquivos são renomeados para o nome final, escolhido por
`naming.unique_path` — nunca sobrescreve. Falha ou cancelamento apagam o staging. Se a pasta de
destino não aceita gravação (CD, Arquivos de Programas), o Alfred usa `Documentos\Alfred` e avisa.

Processos externos (FFmpeg, LibreOffice, Pandoc, 7-Zip, o worker do pdf2docx) rodam sem janela
(`CREATE_NO_WINDOW`), dentro de um **Job Object** com `KILL_ON_JOB_CLOSE`: se o Alfred fechar ou travar,
o Windows encerra todos os filhos. O cancelamento mata a árvore do processo.

## Instância única e segundo plano

- O primeiro processo cria um mutex `Local\alfred-v2-<hash do usuário>` e escuta um `QLocalServer`.
- Execuções seguintes (menu de contexto, Enviar para, atalho, inicialização) enviam o pedido e saem.
  O Explorer abre um processo por arquivo selecionado; o principal **agrega** os pedidos por 350 ms e
  abre uma roda só.
- O X da janela esconde para a bandeja. “Sair” encerra. Logoff/desligamento do Windows não são
  bloqueados (`commitDataRequest`).
- `--quit` (desinstalador) pede para a instância encerrar; `--unregister` remove as integrações.

## Sons

Sintetizados por `tools/gen_sounds.py` (senoides, ruído filtrado, reverberação sintética) — originais,
CC0. No Windows tocam via `PlaySoundW` com os dados em memória (sem latência, sem pilha multimídia
extra). O volume escala as amostras com curva perceptual.

## Dependências nativas e licenças

Veja [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Os binários de FFmpeg e Pandoc vêm de wheels
oficiais do PyPI (`imageio-ffmpeg`, `pypandoc_binary`); 7-Zip e LibreOffice de instalações oficiais.
SVG é renderizado por QtSvg (o v1 usava cairosvg, que exige a DLL do Cairo ausente no Windows).
