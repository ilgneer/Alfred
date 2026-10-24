# Como contribuir

Obrigado por querer ajudar o Alfred! Contribuições de código, testes, traduções e relatos de bugs são
bem-vindas.

## Ambiente

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
$env:PYTHONPATH = "src"
.venv\Scripts\python -m alfred
.venv\Scripts\python -m pytest -q
.venv\Scripts\ruff check src tests tools
```

No Linux/macOS o app abre para desenvolvimento (sem gesto, menu de contexto nem sons, que são do
Windows). Os testes rodam com `QT_QPA_PLATFORM=offscreen`.

## Regras do projeto

1. **Nada de conversões falsas.** Toda nova conversão entra em `src/alfred/core/routes.py` com o motor
   real que a executa e passa por `tests/test_routes_all.py` com um arquivo real e um validador de
   formato em `tests/validators.py`. Se a fidelidade depende muito do conteúdo, marque `EXPERIMENTAL`.
2. **Nunca sobrescrever nem alterar o original.** Use `ctx.stage(...)` para gravar saídas.
3. **Sem bloquear a interface.** Trabalho pesado roda na fila (`core/jobs.py`) e checa `ctx.check()` /
   `ctx.progress(...)` para permitir cancelamento.
4. **Sem hooks globais de teclado/mouse.** O gesto usa amostragem (`platform/gesture.py`).
5. Rode `python tools/gen_matrix.py` quando mudar rotas (há um teste que compara o documento).
6. Textos da interface em português do Brasil; código e comentários podem ser em inglês.
7. Novas dependências: verifique a licença (o projeto é AGPL-3.0) e atualize `THIRD_PARTY_NOTICES.md`.

## Pull requests

- Um assunto por PR, com descrição do problema e de como foi testado.
- CI verde (Linux + Windows).
- Mudanças visuais: anexe capturas (`python tools/screenshots.py`).
- Ao contribuir, você concorda em licenciar sua contribuição sob a AGPL-3.0-or-later.

## Relatando bugs

Use o template “Relatório de bug”. Ajuda muito anexar o log (*Configurações › Avançado › Abrir logs*) e
informar versão do Windows, escala de tela e edição do Alfred.
