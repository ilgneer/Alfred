# Política de segurança

## Versões com suporte

| Versão | Suporte |
|---|---|
| 2.x | ✅ |
| 1.x | ❌ (atualize para a 2.x) |

## Como relatar uma vulnerabilidade

Não abra uma *issue* pública. Use **Security → Report a vulnerability** (GitHub Private Vulnerability
Reporting) neste repositório, com:

- versão do Alfred, edição (Leve/Completa) e versão do Windows;
- passos para reproduzir e, se possível, um arquivo de exemplo (sem dados pessoais);
- impacto esperado.

Você receberá uma resposta assim que possível. Correções são publicadas numa nova versão e creditadas
a quem relatou, se desejar.

## Medidas de segurança do Alfred

- Tudo é processado localmente; o Alfred não faz conexões de rede.
- Extração de compactados protegida contra *path traversal* (*zip-slip*), links simbólicos, arquivos
  protegidos por senha que travariam a extração e conteúdo maior que o espaço livre.
- Saídas gravadas em pasta temporária oculta no destino e renomeadas sem sobrescrever; o original
  nunca é aberto para escrita.
- Processos externos rodam sem console, com tempo limite, e são encerrados junto com o Alfred
  (Job Object do Windows).
- Instalação por usuário (sem administrador) e integrações apenas em `HKEY_CURRENT_USER`.
- Sem ganchos globais de teclado ou mouse.

## Escopo

Arquivos maliciosos que exploram falhas dos motores incluídos (FFmpeg, LibreOffice, MuPDF, libheif,
7-Zip…) devem também ser relatados aos respectivos projetos. O Alfred atualiza esses componentes a
cada versão.
