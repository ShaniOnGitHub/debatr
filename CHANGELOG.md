# Changelog

All notable changes to the Debatr project are documented in this file.

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
