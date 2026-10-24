# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e
[Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [2.0.0] — 2026-10-24

Reescrita completa.

### Adicionado
- Nova interface premium (preto profundo, grafite e dourado, vidro escuro): barra lateral, telas Início,
  Histórico, Atalhos, Configurações e Sobre, transições suaves, fontes Inter/Lora incluídas.
- Roda de conversão redesenhada: só o círculo, sem janela quadrada; segmentos translúcidos com ícones
  grandes; miniatura (imagem, PDF ou vídeo) e nome do arquivo no centro; destaque animado; navegação por
  teclado (setas, Enter, 1–9); posicionamento inteligente em múltiplos monitores.
- Gesto Shift + arrastar reconstruído: a roda é alvo do arrastar nativo do Windows; soltar num formato
  converte, soltar fora cancela, Esc cancela, e o Explorer nunca move o arquivo.
- Modificadores alternativos do gesto (Shift+Ctrl, Shift+Alt) e liga/desliga na bandeja.
- Sons originais (passar o mouse, seleção, abrir, cancelar, concluído, erro) com volume 0–100 % e
  pré-visualização.
- Registro declarativo de conversões (mais de 400 combinações) com matriz gerada automaticamente.
- Motores incluídos: FFmpeg, Pandoc, 7-Zip e LibreOffice (edição Completa) — sem PATH, sem Python.
- PDF → DOCX com reconstrução de layout (pdf2docx), PDF → XLSX com detecção de tabelas, PDF → EPUB/MD,
  páginas a 300 DPI; SVG → PDF vetorial; HEIC/AVIF; GIF com paleta otimizada; remux sem perdas.
- Fila de conversões com progresso real, cancelamento e notificações; histórico das últimas 500.
- Instância única (os pedidos do menu de contexto são agregados numa roda só).
- “Enviar para → Alfred”, menu de contexto, inicialização com o Windows, tudo por usuário (HKCU).
- Instalador Inno Setup com arte própria, edições Leve/Completa, tarefas opcionais, encerramento do app
  e limpeza completa na desinstalação.
- GitHub Actions: CI (Linux + Windows) e release que testa conversões com os motores empacotados, o
  executável, a instalação e a desinstalação.
- ~600 testes automatizados; `--self-test` para diagnosticar instalações.

### Corrigido (em relação ao 1.x)
- Shift + arrastar podia **mover** o arquivo no Explorer ao soltar fora da roda.
- Esc não fechava a roda quando o Explorer estava em primeiro plano.
- Abertura do PowerShell a cada gesto (até 6 s) e gesto disparando fora do Explorer.
- Opções que sempre falhavam (Pages, MD → PDF/DOC sem LaTeX, SVG sem Cairo, HEIC/AVIF sem codec).
- “LibreOffice/FFmpeg/Pandoc/7-Zip necessário — adicione ao PATH”.
- Arquivos parciais deixados após falhas; ausência de cancelamento.
- Uso da área de transferência fora da thread da interface.
- Várias instâncias e vários ícones na bandeja.
- Desinstalação que não encerrava o processo; script de menu de contexto com caminho errado.
- Licença MIT incompatível com PyMuPDF (AGPL) — agora AGPL-3.0-or-later.

### Removido
- Modos “Ferramentas” e “Ações” da roda (copiar/mover/abrir pasta), substituídos por uma roda focada em
  conversão + “Compactar em ZIP” e “PDF único”.
- Arte alternativa com símbolo de morcego no aplicativo e no instalador.

## [1.0.0]
- Protótipo inicial com roda radial, conversões básicas e instalador.
