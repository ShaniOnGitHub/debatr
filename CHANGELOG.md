# Changelog

All notable changes to the Debatr project are documented in this file.

---

## [1.5.0] - 2026-10-04

### Added
- **History Pruning Utility**: Added `prune_history()` to safely retain recent records and archive older debates.
- **Readability Scoring**: Added `calculate_readability_score()` and integrated accessibility metrics into speech analysis.
- **Aggregate CSV Export**: Added `export_history_csv()` to export the entire debate history to spreadsheet-compatible CSV.
- **Dynamic Topic Registration**: Added `register_preset_topic()` to allow runtime registration of custom debate propositions.
- **Expanded Test Suite**: Added 4 comprehensive unit tests, bringing automated test coverage to 39 verified test scenarios.

---

## [1.4.0] - 2026-10-01

### Added
- **HTML Transcript Export**: Added `export_transcript_html()` to generate self-contained, styled HTML debate transcripts.
- **CSV Transcript Export**: Added `export_transcript_csv()` to export tabular speech records for spreadsheet analysis.
- **Date Range Filter**: Added `filter_debates_by_date()` to filter historical debate sessions by timestamp intervals.
- **Lexical Diversity Analysis**: Added `calculate_lexical_diversity()` and integrated vocabulary richness into speech metrics.
- **Preset Topic Search**: Added `search_preset_topics()` to find debate propositions across categories by keyword.
- **Round Turn Exchanges**: Added `get_round_exchanges()` to inspect debate turns side-by-side round-by-round.
- **History Summary Report**: Added `get_history_summary_report()` for aggregated win rates and agreement statistics.
- **Duration Tracking**: Added session duration tracking with `get_duration_seconds()` on the debate orchestrator.
- **Winning Point Differential**: Added `get_winning_margin()` to compute score spreads from judge evaluation cards.
- **Topic Quality Validator**: Added `validate_preset_topic()` to enforce length and clarity constraints.
- **Expanded Test Suite**: Added 10 new unit tests, bringing automated test coverage to 35 verified test scenarios.

---

## [1.3.0] - 2026-09-29

### Added
- **Debate Slug Generator**: Added `generate_debate_slug()` to format debate topics into clean, filesystem-safe filenames.
- **History Backup Utility**: Added `backup_history()` to create timestamped or custom backup copies of the debates history file.
- **Approximate Token Estimator**: Added `estimate_token_count()` and integrated token tracking into speech metrics.
- **Debater Stance Helper**: Added `get_debater_stance()` and `DebateOrchestrator.get_stance()` for clear debater position descriptions.
- **Winner Filter**: Added `filter_debates_by_winner()` to quickly filter past debates by winning debater.
- **Expanded Test Suite**: Added 5 new unit tests, bringing automated test coverage to 25 verified test scenarios.

---

## [1.2.0] - 2026-09-27

### Added
- **Multi-Format Transcripts**: Added JSON export (`export_transcript_json()`) and clean plain text export (`export_transcript_plain_text()`).
- **Speech Metrics**: Implemented `get_speech_metrics()` to calculate word counts and turns per debater.
- **Categorized Presets**: Added `PRESET_TOPICS` categorized across AI, Society, and Science, along with helper accessors.
- **Debate History Querying**: Added `get_recent_debates()` and `search_debates()` to search and inspect history records.
- **Selective Debate Deletion**: Added `delete_debate_by_id()` to remove individual debate records.
- **Lifecycle Status Tracking**: Added `status` property to track the four lifecycle states (`pending`, `in_progress`, `awaiting_vote`, `completed`).
- **Score Averaging**: Added `avg_score_a` and `avg_score_b` computation in running statistics.
- **UI Enhancements**: Added structured JSON transcript downloads and centralized preset topic selection in the Streamlit app.
- **Expanded Test Suite**: Added 10 new unit tests bringing automated test coverage to 20 comprehensive scenarios.

### Changed
- **Input Validation**: Added `sanitize_topic()` to strip extra whitespace and control characters, and enforced `MAX_ROUNDS = 10`.
- **Custom Model Support**: Allowed specifying model override directly in `DebateOrchestrator` constructor.

---

## [1.1.0] - 2026-09-25

### Added
- **Transcript Markdown Export**: Added `export_transcript_markdown()` to format complete debate transcripts, user votes, and judge reasoning as clean Markdown documents.
- **In-App Download Button**: Added a direct button in the web interface to download debate transcripts.
- **Debate Record Lookup**: Added `get_debate_by_id()` to retrieve specific past debate records by their unique identifier.
- **History Reset Utility**: Added `clear_history()` to safely reset past debate history when needed.
- **Configurable History Path**: Supported the `DEBATR_HISTORY_FILE` environment variable to configure the history file location.
- **Automated CI Workflow**: Added GitHub Actions workflow to run the test suite on every push and pull request across Python 3.11 and 3.12.
- **Comprehensive Test Suite**: Added 10 isolated unit tests covering transcript formatting, input validation, JSON parsing edge cases, record lookups, statistical accuracy, and export capabilities.

### Changed
- **Opt-in Live Tests**: Offline and CI test runs now execute instantly without calling external APIs; live model testing is activated with the `--live` flag.
- **Friendly API Errors**: Replaced generic HTTP errors with plain-language explanations for missing API keys, invalid models, and rate limits.
- **Dynamic Model Indicator**: The active model in the user interface now dynamically reflects your configured environment settings.
- **Empty State Display**: The statistics banner now gracefully displays placeholder text before any debates are recorded.

---

## [1.0.0] - 2026-09-17

### Added
- Multi-round debate orchestration between Debater A (FOR) and Debater B (AGAINST).
- Impartial silent AI judge evaluating consistency, evidence, and rebuttal engagement.
- Vote and reveal mechanism holding judge verdict confidential until user votes.
- Streamlit interactive interface with real-time speech streaming.
