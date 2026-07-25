# HExtra PM App v16

Sistema de gestão operacional para ocorrências em eventos da Polícia Militar da Bahia / CPR-CN.

## Funcionalidades

- **Dashboard operacional** com indicadores editáveis
- **Matriz de indicadores por data** com edição in-cell
- **Tabela dinâmica** (PivotTable) com exportação para Excel
- **Cards institucionais** para Instagram (feed, story, reels)
- **Exportação PDF** com card e relatório operacional
- **Importação de planilhas XLSX**
- **Banco de dados SQLite** embutido (sql.js via WebAssembly)

## Como usar

1. Acesse pelo **GitHub Pages**: https://geocria-gif.github.io/H-
2. Ou abra o arquivo `HExtra_PM_App_v16_FINAL.html` diretamente no navegador
3. Importe uma planilha XLSX com os dados de ocorrências ou edite manualmente na matriz
4. Navegue pelas abas para visualizar dashboards, cards e exportar relatórios

## Tecnologias

- HTML/CSS/JS puro (single-file)
- Chart.js (visualizações)
- jsPDF + autoTable (exportação PDF)
- html2canvas (captura de cards)
- sql.js (SQLite via WebAssembly)
- SheetJS (XLSX import/export)
