# Diagnóstico técnico do Alfred 1.x

Análise do projeto anterior (`app.py` + `converters_extra.py`) que motivou a reescrita 2.0.

## Problemas críticos

| # | Problema | Consequência | Solução na 2.0 |
|---|---|---|---|
| 1 | A roda aparecia durante um arrasto Shift (= **mover** no Explorer) e não era alvo de soltar | Soltar na área transparente fazia o Explorer **mover o arquivo** para onde estivesse por trás | A roda e um overlay invisível são alvos OLE; o efeito é sempre COPIAR; fora da roda o drop é recusado |
| 2 | Seleção lida por PowerShell a cada gesto (timeout de 6 s) e gesto ativo em qualquer programa | Atraso e disparos ao selecionar texto com Shift no Word/navegador | Arquivos vêm do próprio arrasto; gesto só nasce em janelas do `explorer.exe` |
| 3 | Janela `Tool` sem foco | Esc não fechava a roda | Esc lido globalmente (sem hook) + foco forçado no modo clique |
| 4 | Opções sem motor: PAGES, MD → PDF/DOC (Pandoc sem LaTeX), SVG via cairosvg (DLL ausente no Windows), HEIC/AVIF sem codec | Itens na roda que sempre falhavam | Registro de rotas com motores verificados + teste real de cada rota |
| 5 | FFmpeg, Pandoc, 7-Zip e LibreOffice exigidos no PATH | “Instale X e adicione ao PATH” | Motores incluídos em `engines/` e localizados por caminho absoluto |
| 6 | Saída gravada direto no nome final | Arquivos corrompidos/parciais após erro | Staging oculto + renomeação final sem sobrescrever |
| 7 | Sem cancelamento e sem progresso real | Interface “presa” em conversões longas | Fila com progresso (FFmpeg `-progress`, páginas) e cancelamento que mata a árvore de processos |
| 8 | `QApplication.clipboard()` usado na thread de trabalho | Risco de travamento | Ação removida da roda; nada de GUI fora da thread principal |
| 9 | Sem instância única | Um processo e um ícone na bandeja por arquivo do menu de contexto | Mutex + canal local; pedidos agregados numa roda |
| 10 | Licença MIT com PyMuPDF (AGPL) embutido | Distribuição em desacordo com a licença | AGPL-3.0-or-later |
| 11 | Arte alternativa com símbolo de morcego | Risco de marca registrada | Retirada do app e do instalador |
| 12 | Instalador sem encerrar o processo; `.bat` de menu com caminho `dist\Alfred.exe` errado; versão escrita em 3 lugares; CI sem testes | Desinstalação com processo residente, integrações quebradas | Inno Setup com `--quit`/taskkill/`--unregister`, versão única em `alfred/__init__.py`, CI que testa até a desinstalação |

## Problemas menores

- Código morto: miniatura comparava a categoria com `'Imagem'` (o valor real era `'Imagens'`); ramos de
  PDF dentro de “Ferramentas” nunca eram alcançados; `ext = action.lower() if mode == 'Converter'`
  dentro de um bloco que só rodava em “Ferramentas”.
- Sons de 85 ms e 250 ms, volume não persistido.
- Configurações não eram salvas; nada de histórico.
- `explorer_selection.ps1` executado com `-ExecutionPolicy Bypass` a cada gesto.
