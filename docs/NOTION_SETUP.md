# Configurando a integração com Notion

O `study-mcp` pode salvar resumos (`save_summary_tool`) e flashcards
(`save_flashcards_tool`) num database do Notion, com a página
renderizada de forma legível (parágrafos pro resumo, blocos toggle
clicáveis pergunta→resposta pros flashcards).

Isso é opcional — sem token configurado, o resto do servidor
(ingest, busca, tools de material) funciona normalmente.

## 1. Criar a integração no Notion

1. Acesse [notion.so/my-integrations](https://www.notion.so/my-integrations)
   e clique em **"New integration"**.
2. Dê um nome (ex: `study-mcp`) e associe ao seu workspace.
3. Em **Capabilities**, marque **Read content**, **Insert content** e
   **Update content**.
4. Salve e copie o **"Internal Integration Secret"** — esse é o
   `NOTION_TOKEN`.

## 2. Criar o database

Duas formas — escolha uma.

### Opção A — Script automático (recomendado)

Cria o database já com as colunas certas, direto na sua conta.

1. No Notion, abra (ou crie) uma página qualquer que vai servir de
   "pasta" pro database, e copie o ID dela: é o trecho de 32
   caracteres no final da URL da página.
2. Rode:
   ```bash
   NOTION_TOKEN=secret_xxxxxxxxxxxx poetry run python \
     scripts/create_notion_database.py <id_da_pagina_pai> "Meu Study DB"
   ```
3. O script imprime o `NOTION_DATABASE_ID` no final — copie esse
   valor.

Como o database é criado pela própria integração, ele já nasce
compartilhado com ela — não precisa fazer o passo 3 da Opção B.

### Opção B — Manual pela interface

Crie uma página nova → **Table** (database), com estas colunas
exatas (nome e tipo têm que bater, são case-sensitive):

| Coluna | Tipo | Obrigatória? |
|---|---|---|
| `Name` | Title | Sim (já vem criada por padrão) |
| `Type` | Select | Sim |
| `Material` | Text | Sim |
| `Content` | Text | Sim |
| `Tags` | Multi-select | Opcional (só usada em `save_summary_tool` se você passar tags) |

Depois, compartilhe o database com a integração: abra o database →
`•••` no canto superior direito → **"Connections"** → selecione a
integração (`study-mcp`). Sem isso a API retorna erro de acesso
negado mesmo com o token certo.

Por fim, pegue o `NOTION_DATABASE_ID` na URL do database (o trecho
de 32 caracteres hexadecimais antes do `?v=`).

## 3. Configurar no Claude Desktop

As credenciais vão no bloco `"env"` do `study-mcp` dentro do
`claude_desktop_config.json` do Claude Desktop — **não** no `.env`
do projeto (o `.env` é só pra rodar/testar localmente fora do Claude
Desktop). Veja `docs/claude_desktop_config.json` neste repo como
referência:

```json
"env": {
  "NOTION_TOKEN": "secret_xxxxxxxxxxxxxxxxxxxxxxxx",
  "NOTION_DATABASE_ID": "1a2b3c4d5e6f7890abcd1234ef567890"
}
```

Depois de editar, **reinicie o Claude Desktop de verdade** (Sair/Quit
completo, não só fechar a janela) — variáveis de ambiente só são
lidas quando o processo do servidor MCP é iniciado.

## Notas técnicas

- O `notion_client` é fixado na versão de API `2022-06-28`
  (`notion_version='2022-06-28'` ao criar o `Client`). A partir de
  `2025-09-03` o Notion passou a exigir `data_source_id` em vez de
  `database_id` como parent de página — fixar a versão evita esse
  refactor e mantém a integração compatível com um único database
  por material, que é o caso de uso aqui.
- Resumos viram blocos de parágrafo reais no corpo da página;
  flashcards viram blocos toggle (pergunta como título clicável,
  resposta escondida dentro). Acima de 100 blocos por página, o
  código faz upload em lotes (limite da API do Notion).
