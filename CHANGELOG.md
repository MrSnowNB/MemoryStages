# MemoryStages Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Stage 6: Privacy Enforcement & Data Protection - 2025-10-06
- **Added**: PrivacyEnforcer class with access validation, backup redaction, audit reporting; Key normalization (canonical camelCase storage); System identity answers (LLM bypass for config/status); Vector search provenance; Privacy-aware backup CLI; docs/PRIVACY.md
- **Fixed**: Multi-layer data protection, case-insensitive lookups with normalized storage, chatbot identity question handling, comprehensive privacy audit trails
- **Tests**: 11/12 privacy enforcement (1 integration mock issue); comprehensive key normalization; system identity bypass; vector provenance reporting; CLI privacy enforcement
- **Notes**: Privacy default disabled; `PRIVACY_ENFORCEMENT_ENABLED=true` enables comprehensive data protection; `KEY_NORMALIZATION_STRICT=true` provides case-insensitive lookups

### Stage 5: TUI/Ops Dashboard - 2025-10-01
- **Added**: TUI dashboard with auth, monitoring, triggers, audit viewer, maintenance tools; CLI utilities; docs/TUI_OPS.md
- **Fixed**: Auth token timing attack prevention, configuration validation, monitor health recursion
- **Tests**: 21/21 auth; 17/21 monitor (mock timing), others as run; dashboard launch verified
- **Notes**: Dashboard default disabled; when enabled, local-only auth token required

### Fixed
- **scripts/rebuild_index.py**: Resolved Pylance import resolution warning for `core.db` module. The import was functional at runtime but Pylance couldn't resolve it due to dynamic path modification.

### Changed
- Added `.vscode/settings.json` with `python.analysis.extraPaths` configuration to include `./src`, allowing Pylance to properly resolve imports in scripts that modify `sys.path` during runtime.

## [1.0.0] - 2025-09-XX

Initial release of MemoryStages Stage 1 implementation.
- SQLite foundation with KV storage
- Basic key-value operations API
- Data access layer with transaction support
- Episodic event logging
- Health check endpoints
