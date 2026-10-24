# Licença: distribuir de graça ou vender

O código do Alfred usa a **GNU Affero General Public License v3.0 ou posterior (AGPL-3.0-or-later)**.

## Por que AGPL (e não MIT, como no v1)?

O Alfred usa o **PyMuPDF/MuPDF**, licenciado em AGPL-3.0 (ou licença comercial paga da Artifex), e
empacota **FFmpeg** (GPL-3.0) e **Pandoc** (GPL-2.0+). Distribuir um executável que inclui o PyMuPDF
sob MIT, como no v1, não respeitava a licença do PyMuPDF. A AGPL resolve isso e continua permitindo
uso livre e venda.

## O que você PODE fazer

- Distribuir o instalador **de graça** no GitHub, no seu site, no canal.
- **Vender** o Alfred (por exemplo, um preço acessível pelo instalador pronto, suporte, atualizações
  antecipadas ou como “apoio ao projeto”). A licença permite cobrar pela distribuição.
- Modificar o código e publicar versões próprias.

## O que você PRECISA fazer

1. **Disponibilizar o código-fonte** correspondente a cada versão distribuída, sob a AGPL, para quem
   recebeu o programa. O repositório público no GitHub com a tag da versão cumpre isso; o botão
   *Código-fonte* do app aponta para ele.
2. Manter os avisos de licença (pasta `licenses/` instalada, tela *Sobre*, `LICENCA_INSTALADOR.txt`).
3. Disponibilizar o código-fonte dos componentes GPL incluídos (FFmpeg, Pandoc): o workflow de release
   anexa `third-party-sources.zip` em cada Release.
4. Se alguém modificar o Alfred e oferecer como serviço pela rede, deve oferecer o código também
   (cláusula “Affero”; não se aplica ao uso normal do aplicativo de desktop).

## O que a licença NÃO impede

- Quem comprar pode redistribuir o programa (inclusive de graça). Isso é da natureza do software livre:
  o que se vende, na prática, é a conveniência, o suporte e a confiança na fonte oficial.
- A **marca e a arte** não estão na AGPL (veja [ASSETS_E_DIREITOS.md](ASSETS_E_DIREITOS.md)): ninguém pode
  vender um fork usando o seu logotipo e o seu personagem.

## Alternativa

Se no futuro você quiser um modelo fechado (sem publicar o código), seria necessário comprar a licença
comercial do PyMuPDF (Artifex), trocar o FFmpeg por uma compilação LGPL sem codificadores GPL e
reavaliar Pandoc/pdf2docx. Isso exigiria mudanças de código e custos.

*Este texto é informativo e não substitui orientação jurídica.*
