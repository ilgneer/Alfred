# Testes e qualidade

Este documento separa com clareza **o que foi testado de verdade**, **o que é verificação estática** e
**o que ainda depende de teste manual no Windows**.

## 1. Testes automatizados (pytest)

`python -m pytest -q` — cerca de 600 testes:

| Arquivo | O que verifica |
|---|---|
| `test_routes_all.py` | **Cada** combinação origem → destino → plano do registro é executada com um arquivo real (nome com acento, pasta com espaços) e a saída é validada por formato (Pillow abre a imagem, FFmpeg decodifica o áudio/vídeo inteiro, PyMuPDF abre o PDF, python-docx/pptx/openpyxl abrem os arquivos Office, `mimetype` de EPUB/ODF, cabeçalho OLE de DOC/XLS/PPT, UTF-8 de textos…). Rotas cujo motor não existe na máquina aparecem como *SKIPPED* com o motivo — nunca como aprovadas. |
| `test_content.py` | Preservação de conteúdo: texto de DOCX → PDF (com e sem LibreOffice), PDF → DOCX/TXT/MD/XLSX, CSV brasileiro (`;`, vírgula decimal, Windows-1252) → XLSX tipado, XLSX → CSV por aba, tempos de legenda SRT ↔ VTT, vozes VTT, SVG → PDF vetorial, TIFF multipágina → PDF, duração de áudio/vídeo, remux sem perdas, conteúdo de ZIP/RAR/TAR. |
| `test_safety.py` | Nunca sobrescreve; original intacto; falha não deixa arquivo parcial; lote parcial; **cancelamento de um FFmpeg longo em < 10 s sem sobras**; ZIP *zip-slip*; TAR com link simbólico; RAR com *symlink traversal*; RAR com senha não trava; destino sem permissão → `Documentos\Alfred`; imagem de 108 MP; 25 arquivos de uma vez; rotas somem quando falta motor; seleção mista; nunca oferece o mesmo formato. |
| `test_gesture.py` | Máquina de estados do Shift + arrastar: limiar, origem fora do Explorer, Shift-clique, Esc, modificadores alternativos, repetição. |
| `test_radial.py` | Geometria dos segmentos (1–12 itens), posicionamento nas bordas e em monitor secundário com coordenadas negativas, Esc, setas/Enter/1–9, clique em segmento/centro/fora, **drop OLE sempre como COPIAR**, drop fora recusado, drop no centro fixa a roda, overlay nunca aceita drop, janela sem moldura e **cantos 100 % transparentes**. |
| `test_app.py` | Controlador real off-screen: abrir/cancelar a roda, fluxo completo até o histórico e a notificação, fechar para a bandeja, persistência e normalização de configurações, recuperação de arquivo corrompido, instância única agregando arquivos, sons (formato, duração, escala de volume), histórico limitado a 500, autoteste. |
| `test_windows.py` | Só no Windows (CI): helpers Win32, registro (menu/inicialização) ida e volta, cancelamento mata a árvore de processos, backend de som `PlaySoundW`, mutex de instância única exclusivo entre processos. |

### Onde rodam

- **CI (`ci.yml`)**: Linux (com LibreOffice e 7-Zip) e Windows a cada push/PR.
- **Release (`release.yml`)**: Windows, **com os motores que vão dentro do instalador**, antes de
  empacotar; depois o executável faz `--self-test`; depois o instalador é instalado, testado e
  desinstalado por `tools/test_installer.ps1`.

## 2. Execuções reais feitas durante o desenvolvimento desta versão

Ambiente: contêiner Linux x86-64 (Qt off-screen), sem Windows.

- Suíte completa em **Python 3.13** e em **Python 3.12 com as versões fixadas** de `requirements*.txt`:
  **597 aprovados, 5 ignorados** (os 5 são exclusivos do Windows).
- Build **PyInstaller** real (Linux) com o mesmo `alfred.spec`: o executável congelado passou no
  `--self-test` (19 conversões, incluindo PDF → DOCX pelo processo-filho e motores “incluídos”).
- Executável congelado: pedidos de outras execuções (abrir arquivo, `--background`) entregues à instância
  principal em ~0,3 s cada; `--quit` encerrou a instância residente sem deixar processo.
- Esses testes encontraram e corrigiram, entre outros: rota DOC → PDF sem LibreOffice (Pandoc não lê
  .doc), GIF com dois fluxos de saída, TIFF multipágina perdendo páginas, binário do FFmpeg não
  encontrado em Linux e uma condição de corrida no canal de instância única.
- Capturas da interface geradas pela própria interface Qt (`tools/screenshots.py`).

## 3. Verificações estáticas

- `ruff check src tests tools` (pyflakes, pycodestyle, bugbear, pyupgrade, simplify, imports) — sem erros.
- `python -m compileall src tools` — sem erros de sintaxe.
- `docs/COMPATIBILIDADE.md` é gerado do registro de rotas (`tools/gen_matrix.py`), e um teste falha se
  o documento ficar desatualizado.

## 4. NÃO testado ainda (depende de Windows real) — roteiro manual

Estes itens só podem ser confirmados num Windows com área de trabalho. O workflow de release cobre a
instalação/desinstalação silenciosa, mas **não** a interação humana. Antes de divulgar, faça:

| # | Teste | Esperado |
|---|---|---|
| 1 | Instalar a edição Completa num Windows 11 limpo (sem Python/LibreOffice) | Assistente com logo, idioma pt-BR, tarefas marcadas, Alfred abre ao final |
| 2 | Explorer: selecionar 1 JPG e arrastar com **Shift** | Roda aparece no cursor, sem fundo quadrado; miniatura no centro |
| 3 | Passar pelos segmentos | Destaque dourado animado + clique sonoro discreto |
| 4 | Soltar sobre **PNG** | Som de seleção, notificação com progresso, `foto.png` ao lado do original |
| 5 | Repetir e apertar **Esc** com a roda aberta | Fecha na hora; nenhum arquivo criado, movido ou copiado |
| 6 | Repetir e **soltar fora da roda** | Cursor “proibido” fora da roda; nada acontece com o arquivo |
| 7 | Selecionar 5 arquivos variados + Shift + arrastar | Roda mostra só destinos comuns; soltar converte todos |
| 8 | Shift + arrastar no espaço vazio (seleção por retângulo) | Seleção normal do Explorer, roda **não** abre |
| 9 | Shift + arrastar texto no Word/navegador | Comportamento normal, roda não abre |
| 10 | Segundo monitor (escala diferente, ex.: 150 %) | Roda nítida e inteira na tela, perto do cursor |
| 11 | Cursor nos cantos da tela | Roda reposicionada dentro da área visível |
| 12 | Clique direito → *Mostrar mais opções* → Converter com Alfred (vários arquivos) | Uma roda só, com todos os arquivos |
| 13 | Enviar para → Alfred | Roda abre |
| 14 | Fechar a janela no **X** | Some, ícone continua na bandeja, gesto continua funcionando |
| 15 | Menu da bandeja | Abrir, Configurações, Integração (liga/desliga gesto), Sons, Sobre, Sair |
| 16 | Configurações › Sons: volume 0, 50, 100 e pré-visualizações | Volume audível no padrão (80 %), sem estalos |
| 17 | Converter vídeo de 1 GB e cancelar no meio | Para em segundos, sem arquivo parcial |
| 18 | DOCX → PDF, PPTX → PDF, XLS → XLSX (edição Completa) | Funcionam sem nenhum LibreOffice instalado no sistema |
| 19 | Reiniciar o Windows | Alfred volta na bandeja (se a opção estiver marcada) |
| 20 | Desinstalar pelo Painel de Controle com o Alfred aberto | Encerra o app, pergunta sobre os dados, remove menu, atalhos e inicialização |
| 21 | Windows 10 22H2 | Repetir 1–20 |

Registre problemas com o template de *issue* “Relatório de bug”.
