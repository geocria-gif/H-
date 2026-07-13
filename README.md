# SISPM - Sistema de Escalas do CPR-CN

Sistema web single-page para gestão de escalas de hora extra (HE), vale-transporte (VD) e serviço ordinário (SO) do CPR-CN (Comando de Policiamento Rodoviário - Canto da Lagoa).

## Funcionalidades

- **Dashboard** com indicadores e gráfico de ocorrências
- **Nova Ocorrência** com cadastro de ocorrências no mapa
- **Escala HE / VD** — geração de escala geral mensal com busca por matrícula/nome
- **Escalas Salvas** — snapshots da escala para cálculos do relatório
- **Relatório de Horas** — relatório mensal de HE/VD por militar
- **Tabela de Valores** — configuração de valores por posto/graduação
- **Usuários** — gerenciamento de operadores (admin apenas)
- **Backup / Restore** — exportar/importar o banco de dados SQLite

## Tecnologias

- SQLite via WASM (sql.js)
- JavaScript puro — sem frameworks
- Leaflet.js para mapas
- XLSX export com SheetJS

## Deploy

O app roda 100% no navegador. Para publicar no GitHub Pages:

```bash
git checkout -b gh-pages
git push origin gh-pages
```

Ou configure o repositório em **Settings > Pages** para usar a branch `main` com pasta `/` (root).

## Uso

1. Abra o `index.html` (localmente ou via GitHub Pages)
2. Login: matrícula `30481332`, senha `30481332`
3. O banco de dados começa vazio — use **Backup > Salvar** para baixar e **Carregar** para restaurar
