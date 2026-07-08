-- Diagnóstico de duplicatas em tabelas PostGIS (executar manualmente após carga).

-- Fatos: duplicatas por chave natural (ano, mes, uf, municipio)
SELECT
    ano,
    mes,
    uf,
    municipio,
    COUNT(*) AS qtd
FROM serving.fact_emprego_municipio_mes
GROUP BY ano, mes, uf, municipio
HAVING COUNT(*) > 1
ORDER BY qtd DESC;

-- Geometrias: duplicatas por cod_municipio (não deveria ocorrer com PK)
SELECT
    cod_municipio,
    COUNT(*) AS qtd
FROM geo.municipios
GROUP BY cod_municipio
HAVING COUNT(*) > 1
ORDER BY qtd DESC;

-- Totais de saldo por competência (comparar antes/depois de reexecutar loader)
SELECT
    ano,
    mes,
    uf,
    COUNT(*) AS municipios,
    SUM(saldo) AS saldo_total,
    SUM(admissoes) AS admissoes_total,
    SUM(desligamentos) AS desligamentos_total
FROM serving.fact_emprego_municipio_mes
GROUP BY ano, mes, uf
ORDER BY ano, mes, uf;
