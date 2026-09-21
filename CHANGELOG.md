# Changelog

Registro das mudanças relevantes do produto. Datas aproximadas quando a versão não é semântica.

## Unreleased

### Added

- ICTT methodology version 2.0 (quatro dimensões, NORM_B congelada)
- Pipeline Gold versionado `ictt_v2`
- API `/api/ict/v2/*`
- Dashboard ICTT v2 (mapa, ranking N10/N20, detalhe municipal, metodologia)

### Changed

- `/ict` passa a servir ICTT v2.0

### Compatibility

- ICTT v1 permanece temporariamente em `/ict-v1`
- `/ict-v2` redireciona para `/ict`
- Gold V1 (`tabela_ictt_municipio`) e `/api/ict/v1` não foram removidos
