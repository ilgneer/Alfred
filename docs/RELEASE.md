# Publicar o Alfred no GitHub e gerar o instalador

Guia para quem nunca publicou um projeto. Nada aqui exige Windows próprio: o GitHub compila e testa o
instalador num computador Windows na nuvem, de graça para repositórios públicos.

## 1. Criar o repositório

1. Acesse <https://github.com/new>.
2. Nome sugerido: `alfred`. Visibilidade: **Public**.
3. **Não** marque “Add a README”, “.gitignore” nem “license” — o projeto já tem todos.
4. Clique em **Create repository**.

## 2. Enviar os arquivos

### Opção A — GitHub Desktop (mais fácil)

1. Instale o [GitHub Desktop](https://desktop.github.com/) e entre na sua conta.
2. *File → Add local repository…* e escolha a pasta descompactada do Alfred
   (se ele perguntar, aceite “create a repository”).
3. Escreva um resumo como “Alfred 2.0.0” e clique em **Commit to main**.
4. Clique em **Publish repository** (desmarque “Keep this code private”).

### Opção B — Terminal

```bash
cd Alfred
git init
git add .
git commit -m "Alfred 2.0.0"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/alfred.git
git push -u origin main
```

> Pastas que começam com ponto (`.github`) precisam ir junto: elas contêm os workflows.
> Se você enviar pelo navegador (*Add file → Upload files*), confirme que `.github/workflows` aparece.

## 3. Gerar os instaladores

1. No repositório, abra a aba **Actions** e, se pedir, clique em *I understand… enable them*.
2. Escolha **Release (instaladores Windows)** → **Run workflow** → **Run workflow**.
3. Aguarde (40–90 min: o workflow instala, testa e desinstala o Alfred nas duas edições).
4. Abra a execução concluída e baixe os artefatos **Alfred-Setup-full** e **Alfred-Setup-lite**.

Se algum passo ficar vermelho, clique nele para ver o log — os testes dizem exatamente o que falhou.

## 4. Publicar uma versão (Release)

O jeito automático é criar uma *tag*:

```bash
git tag v2.0.0
git push origin v2.0.0
```

O workflow roda sozinho e cria um **rascunho de Release** com os dois instaladores,
`SHA256SUMS.txt` e `third-party-sources.zip` (código-fonte dos componentes GPL). Revise o texto e
clique em **Publish release**.

Pelo navegador: *Releases → Draft a new release → Choose a tag → digite `v2.0.0` → Create new tag* e
publique; o workflow é disparado pela tag.

- A tag precisa bater com `__version__` em `src/alfred/__init__.py` (o workflow confere).
- Tags com hífen (`v2.1.0-beta1`) viram *pre-release*.

## 5. Antes de divulgar no canal

- Faça o roteiro de testes manuais em [TESTES.md](TESTES.md) num Windows 10 e num Windows 11
  **sem Python e sem LibreOffice instalados** (de preferência numa máquina virtual).
- Teste o gesto com 1 e com vários arquivos, em monitores diferentes e com escala de tela 100 % e 150 %.
- Confirme o aviso do SmartScreen e como orientar seus inscritos (ver README).
- Opcional, mas recomendado: assinar o instalador com um certificado de *code signing*
  (reduz o aviso do SmartScreen). O workflow tem espaço para um passo de assinatura antes do upload.

## 6. Atualizar a versão

1. Altere `__version__` em `src/alfred/__init__.py`.
2. Registre as mudanças no `CHANGELOG.md`.
3. Faça commit, crie a tag `vX.Y.Z` e envie (passo 4). O instalador novo atualiza a instalação
   existente (mesmo `AppId`) e preserva configurações e histórico.

## 7. Endereço do repositório dentro do app

O botão **Código-fonte** (tela *Sobre*) aponta automaticamente para o repositório onde o workflow
rodou. Em builds locais, use `python tools/build.py --repo-url https://github.com/SEU_USUARIO/alfred`.
