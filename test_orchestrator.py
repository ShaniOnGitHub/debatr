import sys
import os
import tempfile
import json
from orchestrator import (
    DebateOrchestrator,
    get_history_stats,
    get_debate_by_id,
    clear_history,
    sanitize_topic,
    MAX_ROUNDS,
    get_recent_debates,
    search_debates,
    delete_debate_by_id,
    PRESET_TOPICS,
    get_preset_categories,
    get_topics_for_category,
    search_preset_topics,
    generate_debate_slug,
    backup_history,
    estimate_token_count,
    get_debater_stance,
    filter_debates_by_winner,
    filter_debates_by_date,
    calculate_lexical_diversity,
    get_history_summary_report,
    get_winning_margin,
    validate_preset_topic,
    prune_history,
    calculate_readability_score,
    export_history_csv,
)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def test_mock_vote_reveal_ordering():
    print("\n=== TEST 1: Mock Vote/Reveal Ordering & Privacy ===")
    
    # Use isolated temporary history file for testing
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_history_path = tf.name
    
    original_history_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_history_path
    
    try:
        orch = DebateOrchestrator(topic="Should AI replace human programmers?", total_rounds=1)

    
        # 1. Simulate turns
        orch.transcript.append({"speaker": "A", "round": 1, "text": "AI increases productivity dramatically."})
        orch.transcript.append({"speaker": "B", "round": 1, "text": "AI lacks true contextual intuition and critical problem solving."})
        
        # 2. Simulate silent judge evaluation
        mock_verdict = {
            "winner": "A",
            "scores": {
                "A": {"logical_consistency": 9, "evidence_use": 8, "rebuttal_engagement": 8, "total": 25},
                "B": {"logical_consistency": 8, "evidence_use": 7, "rebuttal_engagement": 7, "total": 22}
            },
            "reasoning": "Debater A demonstrated more compelling systemic leverage."
        }
        orch._judge_verdict = mock_verdict
        
        # Assert judge verdict is NOT yet revealed
        assert orch.revealed_verdict is None, "CRITICAL: Verdict leaked before user vote!"
        assert orch.user_vote is None, "User vote should be None before voting"
        print("✓ Confirmed: Judge verdict is silent and hidden prior to user voting.")
        
        # 3. User votes for B
        revealed = orch.submit_user_vote("B")
        
        # Assertions after voting
        assert orch.revealed_verdict is not None, "Verdict should now be revealed"
        assert revealed["winner"] == "A"
        assert revealed["user_vote"] == "B"
        assert revealed["agreed_with_ai"] is False, "User vote B does not match Judge winner A"
        print("✓ Confirmed: After user voted 'B', verdict revealed: User agreed = False.")
        
        # 4. Check stats persistence
        stats = get_history_stats()
        print(f"✓ Confirmed: Cumulative stats recorded. Total debates: {stats['total_debates']}, Agreement rate: {stats['agreement_rate']}%")
        print("=== TEST 1 PASSED ===\n")
    finally:
        if original_history_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = original_history_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_history_path):
            try:
                os.remove(temp_history_path)
            except Exception:
                pass



def test_live_llm_debate():
    print("=== TEST 2: Live LLM Debate with stealth/union-alpha ===")
    topic = "Cats are better pets than dogs"
    orch = DebateOrchestrator(topic=topic, total_rounds=1)
    
    print(f"Topic: {topic}")
    print("\n--- Round 1: Debater A (FOR) ---")
    sys.stdout.write("Debater A: ")
    sys.stdout.flush()
    for token in orch.stream_turn("A", 1):
        sys.stdout.write(token)
        sys.stdout.flush()
    print("\n")
    
    print("--- Round 1: Debater B (AGAINST) ---")
    sys.stdout.write("Debater B: ")
    sys.stdout.flush()
    for token in orch.stream_turn("B", 1):
        sys.stdout.write(token)
        sys.stdout.flush()
    print("\n")
    
    print("--- Running Silent LLM Judge Evaluation in Background ---")
    orch.evaluate_judge_silently()
    
    assert orch.revealed_verdict is None, "CRITICAL: Judge verdict revealed before vote!"
    print("✓ Background Judge evaluation completed. Verdict is currently LOCKED.")
    
    # Simulate user voting
    user_choice = "A"
    print(f"\nUser casts vote: {user_choice}")
    revealed = orch.submit_user_vote(user_choice)
    
    print(f"\n--- JUDGE VERDICT UNLOCKED ---")
    print(f"Judge Winner: Debater {revealed['winner']}")
    print(f"User Agreed: {revealed['agreed_with_ai']}")
    print(f"Scores: {revealed.get('scores')}")
    print(f"Reasoning: {revealed.get('reasoning')}")
    
    stats = get_history_stats()
    print(f"\nUpdated Agreement Stats: {stats['agreement_rate']}% across {stats['total_debates']} debate(s).")
    print("=== TEST 2 PASSED ===\n")


def test_history_stats_structure():
    print("=== TEST 3: History Statistics Structure ===")
    stats = get_history_stats()
    expected_keys = {
        "total_debates",
        "agreement_count",
        "agreement_rate",
        "user_wins_a",
        "user_wins_b",
        "judge_wins_a",
        "judge_wins_b",
        "avg_score_a",
        "avg_score_b",
    }
    assert expected_keys.issubset(stats.keys()), f"Missing keys in stats: {expected_keys - stats.keys()}"
    assert isinstance(stats["total_debates"], int), "total_debates should be an integer"
    assert isinstance(stats["agreement_rate"], (int, float)), "agreement_rate should be a number"
    print("✓ Confirmed: History stats returned valid keys and correct types.")
    print("=== TEST 3 PASSED ===\n")


def test_transcript_formatting():
    print("=== TEST 4: Transcript Formatting ===")
    orch = DebateOrchestrator(topic="Renewable energy should replace fossil fuels completely", total_rounds=2)
    assert orch.get_transcript_text() == "No arguments made yet."
    
    orch.transcript.append({"speaker": "A", "round": 1, "text": "Solar and wind are now cheaper than coal."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "Grid storage is not yet ready for baseline power."})
    
    formatted = orch.get_transcript_text()
    assert "Round 1 - Debater A (FOR):" in formatted
    assert "Solar and wind are now cheaper than coal." in formatted
    assert "Round 1 - Debater B (AGAINST):" in formatted
    assert "Grid storage is not yet ready for baseline power." in formatted
    print("✓ Confirmed: Transcript formatting outputs clean speaker and round sections.")
    print("=== TEST 4 PASSED ===\n")


def test_debate_input_validation():
    print("=== TEST 5: Input Validation for Topic and Rounds ===")
    # Empty string topic
    try:
        DebateOrchestrator(topic="")
        assert False, "Should raise ValueError on empty topic"
    except ValueError as e:
        assert "Debate topic cannot be empty." in str(e)
        
    # Whitespace only topic
    try:
        DebateOrchestrator(topic="   ")
        assert False, "Should raise ValueError on whitespace-only topic"
    except ValueError as e:
        assert "Debate topic cannot be empty." in str(e)
        
    # Zero or negative rounds
    try:
        DebateOrchestrator(topic="Valid topic", total_rounds=0)
        assert False, "Should raise ValueError on zero rounds"
    except ValueError as e:
        assert "Total rounds must be a positive integer" in str(e)
        
    try:
        DebateOrchestrator(topic="Valid topic", total_rounds=-2)
        assert False, "Should raise ValueError on negative rounds"
    except ValueError as e:
        assert "Total rounds must be a positive integer" in str(e)

    # Exceeding maximum rounds
    try:
        DebateOrchestrator(topic="Valid topic", total_rounds=MAX_ROUNDS + 1)
        assert False, f"Should raise ValueError when rounds exceed {MAX_ROUNDS}"
    except ValueError as e:
        assert f"Total rounds cannot exceed {MAX_ROUNDS}" in str(e)
        
    print("✓ Confirmed: Invalid topic and round counts are rejected with clear errors.")
    print("=== TEST 5 PASSED ===\n")


def test_parse_judge_json_edge_cases():
    print("=== TEST 6: Judge Response Parsing Edge Cases ===")
    orch = DebateOrchestrator(topic="Remote work increases overall company productivity", total_rounds=1)
    
    # 1. Clean JSON
    clean_json = '{"winner": "B", "scores": {"A": {"total": 20}, "B": {"total": 25}}, "reasoning": "Clearer points."}'
    res1 = orch._parse_judge_json(clean_json)
    assert res1["winner"] == "B"
    assert res1["reasoning"] == "Clearer points."
    
    # 2. Markdown fenced code block
    fenced_json = '```json\n{"winner": "A", "scores": {}, "reasoning": "Strong evidence."}\n```'
    res2 = orch._parse_judge_json(fenced_json)
    assert res2["winner"] == "A"
    
    # 3. JSON embedded within extra commentary
    surrounded_json = 'Here is the verdict:\n{"winner": "B", "reasoning": "B rebutted effectively."}\nHope this helps!'
    res3 = orch._parse_judge_json(surrounded_json)
    assert res3["winner"] == "B"
    
    # 4. Corrupted / unparseable JSON falls back to safe default
    corrupted = "I cannot determine a winner as this is invalid output"
    res4 = orch._parse_judge_json(corrupted)
    assert "winner" in res4
    assert "scores" in res4
    assert "reasoning" in res4
    
    print("✓ Confirmed: Judge JSON parser cleanly handles markdown fences, extra text, and corrupt responses.")
    print("=== TEST 6 PASSED ===\n")


def test_get_debate_by_id():
    print("=== TEST 7: Get Debate By ID ===")
    import json
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        # Non-existent file / empty
        assert get_debate_by_id("non-existent-id") is None
        assert get_debate_by_id("") is None
        
        sample_records = [
            {"id": "test-uuid-1", "topic": "Topic 1", "winner": "A"},
            {"id": "test-uuid-2", "topic": "Topic 2", "winner": "B"}
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(sample_records, f)
            
        found = get_debate_by_id("test-uuid-2")
        assert found is not None
        assert found["topic"] == "Topic 2"
        assert found["winner"] == "B"
        
        not_found = get_debate_by_id("unknown-id")
        assert not_found is None
        print("✓ Confirmed: get_debate_by_id successfully finds matching records and handles missing IDs.")
        print("=== TEST 7 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_export_transcript_markdown():
    print("=== TEST 8: Export Transcript to Markdown ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        orch = DebateOrchestrator(topic="Social media creates more harm than good", total_rounds=1)
        empty_md = orch.export_transcript_markdown()
        assert "# Debate: Social media creates more harm than good" in empty_md
        assert "_No arguments recorded yet._" in empty_md
        
        orch.transcript.append({"speaker": "A", "round": 1, "text": "Social media reduces attention spans."})
        orch.transcript.append({"speaker": "B", "round": 1, "text": "Social media empowers global communities."})
        orch._judge_verdict = {"winner": "A", "reasoning": "A presented stronger psychological research."}
        orch.submit_user_vote("A")
        
        full_md = orch.export_transcript_markdown()
        assert "### Round 1 — Debater A (FOR)" in full_md
        assert "Social media reduces attention spans." in full_md
        assert "### Round 1 — Debater B (AGAINST)" in full_md
        assert "## Official Verdict" in full_md
        assert "**Judge Winner**: Debater A" in full_md
        assert "A presented stronger psychological research." in full_md
        
        print("✓ Confirmed: Markdown export correctly includes debate metadata, speeches, and verdict.")
        print("=== TEST 8 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass



def test_clear_history():
    print("=== TEST 9: Clear History Utility ===")
    import json
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        # Populate with dummy data
        dummy_data = [{"id": "1", "agreed": True, "user_vote": "A", "judge_winner": "A"}]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(dummy_data, f)
            
        assert get_history_stats()["total_debates"] == 1
        
        # Clear history
        success = clear_history()
        assert success is True
        
        # Verify empty
        with open(temp_path, "r", encoding="utf-8") as f:
            content = json.load(f)
        assert content == []
        assert get_history_stats()["total_debates"] == 0
        
        print("✓ Confirmed: clear_history safely resets history to an empty list.")
        print("=== TEST 9 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_history_stats_calculations():
    print("=== TEST 10: History Statistics Edge Cases & Calculations ===")
    import json
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        # Case 1: Empty list
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        stats = get_history_stats()
        assert stats["total_debates"] == 0
        assert stats["agreement_rate"] == 0.0
        
        # Case 2: 2 debates: 1 agreed, 1 disagreed with scores
        mock_data = [
            {"id": "d1", "user_vote": "A", "judge_winner": "A", "agreed": True, "scores": {"A": {"total": 24}, "B": {"total": 20}}},
            {"id": "d2", "user_vote": "B", "judge_winner": "A", "agreed": False, "scores": {"A": {"total": 26}, "B": {"total": 22}}},
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)
            
        stats = get_history_stats()
        assert stats["total_debates"] == 2
        assert stats["agreement_count"] == 1
        assert stats["agreement_rate"] == 50.0
        assert stats["user_wins_a"] == 1
        assert stats["user_wins_b"] == 1
        assert stats["judge_wins_a"] == 2
        assert stats["judge_wins_b"] == 0
        assert stats["avg_score_a"] == 25.0
        assert stats["avg_score_b"] == 21.0
        
        print("✓ Confirmed: Statistical counts and agreement rates are mathematically exact.")
        print("=== TEST 10 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_sanitize_topic():
    print("\n=== TEST 11: Sanitize Topic Helper ===")
    assert sanitize_topic("  Should AI be regulated?  ") == "Should AI be regulated?"
    assert sanitize_topic("Multiple   spaces\t\nand   tabs") == "Multiple spaces and tabs"
    assert sanitize_topic("Clean topic") == "Clean topic"
    assert sanitize_topic("   ") == ""
    assert sanitize_topic(None) == ""
    assert sanitize_topic(123) == ""
    print("✓ Confirmed: Topic sanitization strips whitespace and control characters cleanly.")
    print("=== TEST 11 PASSED ===\n")


def test_custom_model_override():
    print("=== TEST 12: Custom Model Override ===")
    orch_custom = DebateOrchestrator(topic="Custom model topic", model="anthropic/claude-3-opus")
    assert orch_custom.model == "anthropic/claude-3-opus"
    
    orch_default = DebateOrchestrator(topic="Default model topic")
    assert orch_default.model is None
    
    orch_whitespace = DebateOrchestrator(topic="Whitespace model topic", model="   ")
    assert orch_whitespace.model is None
    print("✓ Confirmed: Custom model parameter is correctly parsed and stored.")
    print("=== TEST 12 PASSED ===\n")


def test_speech_metrics():
    print("=== TEST 13: Speech Metrics Calculation ===")
    orch = DebateOrchestrator(topic="Testing speech metrics", total_rounds=1)
    empty_metrics = orch.get_speech_metrics()
    assert empty_metrics["words_a"] == 0
    assert empty_metrics["words_b"] == 0
    assert empty_metrics["total_words"] == 0
    assert empty_metrics["avg_words_per_turn"] == 0.0

    orch.transcript.append({"speaker": "A", "round": 1, "text": "Four words in speech."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "Six words in this debater speech."})
    
    metrics = orch.get_speech_metrics()
    assert metrics["words_a"] == 4
    assert metrics["words_b"] == 6
    assert metrics["turns_a"] == 1
    assert metrics["turns_b"] == 1
    assert metrics["total_words"] == 10
    assert metrics["avg_words_per_turn"] == 5.0
    print("✓ Confirmed: Word counts and speech metrics calculate correctly.")
    print("=== TEST 13 PASSED ===\n")


def test_export_transcript_json():
    print("=== TEST 14: Export Transcript to JSON ===")
    orch = DebateOrchestrator(topic="Testing JSON export", total_rounds=1)
    orch.transcript.append({"speaker": "A", "round": 1, "text": "Point FOR"})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "Point AGAINST"})
    
    json_str = orch.export_transcript_json()
    parsed = json.loads(json_str)
    assert parsed["id"] == orch.id
    assert parsed["topic"] == "Testing JSON export"
    assert parsed["rounds"] == 1
    assert len(parsed["speeches"]) == 2
    assert parsed["metrics"]["total_words"] == 4
    assert parsed["verdict"] is None
    print("✓ Confirmed: JSON transcript exports valid, structured debate data.")
    print("=== TEST 14 PASSED ===\n")


def test_export_transcript_plain_text():
    print("=== TEST 15: Export Transcript to Plain Text ===")
    orch = DebateOrchestrator(topic="Remote work productivity", total_rounds=1)
    empty_txt = orch.export_transcript_plain_text()
    assert "DEBATE TOPIC: Remote work productivity" in empty_txt
    assert "No arguments recorded yet." in empty_txt

    orch.transcript.append({"speaker": "A", "round": 1, "text": "Remote work saves commute time."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "In-person work builds team culture."})
    
    txt = orch.export_transcript_plain_text()
    assert "Round 1 - Debater A (FOR):" in txt
    assert "Remote work saves commute time." in txt
    assert "Round 1 - Debater B (AGAINST):" in txt
    assert "In-person work builds team culture." in txt
    print("✓ Confirmed: Plain text transcript export formats clean text.")
    print("=== TEST 15 PASSED ===\n")


def test_debate_status_lifecycle():
    print("=== TEST 16: Debate Status Lifecycle ===")
    orch = DebateOrchestrator(topic="Lifecycle tracking", total_rounds=1)
    assert orch.status == "pending"
    
    orch.transcript.append({"speaker": "A", "round": 1, "text": "Opening argument."})
    assert orch.status == "in_progress"
    
    orch._judge_verdict = {"winner": "A", "scores": {}, "reasoning": "Good"}
    assert orch.status == "awaiting_vote"
    
    orch.revealed_verdict = {"winner": "A", "user_vote": "A", "agreed_with_ai": True}
    assert orch.status == "completed"
    print("✓ Confirmed: Debate lifecycle status transitions correctly across all stages.")
    print("=== TEST 16 PASSED ===\n")


def test_get_recent_debates():
    print("=== TEST 17: Get Recent Debates ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        assert get_recent_debates(5) == []
        assert get_recent_debates(0) == []
        assert get_recent_debates(-1) == []

        mock_history = [
            {"id": "d1", "topic": "Topic 1"},
            {"id": "d2", "topic": "Topic 2"},
            {"id": "d3", "topic": "Topic 3"},
            {"id": "d4", "topic": "Topic 4"},
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_history, f)

        recent_2 = get_recent_debates(2)
        assert len(recent_2) == 2
        assert recent_2[0]["id"] == "d4"
        assert recent_2[1]["id"] == "d3"

        recent_all = get_recent_debates(10)
        assert len(recent_all) == 4
        assert recent_all[0]["id"] == "d4"
        assert recent_all[3]["id"] == "d1"
        print("✓ Confirmed: get_recent_debates returns recent records in reverse order.")
        print("=== TEST 17 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_search_debates():
    print("=== TEST 18: Search Debates Helper ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        assert search_debates("anything") == []
        assert search_debates("") == []
        assert search_debates("   ") == []

        mock_data = [
            {"id": "s1", "topic": "Should space exploration receive government funding?", "reasoning": "Space drives innovation."},
            {"id": "s2", "topic": "Remote work vs office work", "reasoning": "Higher worker productivity."}
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        res_topic = search_debates("space")
        assert len(res_topic) == 1
        assert res_topic[0]["id"] == "s1"

        res_reasoning = search_debates("PRODUCTIVITY")
        assert len(res_reasoning) == 1
        assert res_reasoning[0]["id"] == "s2"

        res_none = search_debates("cryptocurrency")
        assert len(res_none) == 0
        print("✓ Confirmed: search_debates finds matching topics and reasoning case-insensitively.")
        print("=== TEST 18 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_delete_debate_by_id():
    print("=== TEST 19: Delete Debate By ID ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        assert delete_debate_by_id("") is False
        assert delete_debate_by_id(None) is False
        assert delete_debate_by_id("non-existent") is False

        mock_data = [
            {"id": "del-1", "topic": "Topic 1"},
            {"id": "del-2", "topic": "Topic 2"}
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        assert delete_debate_by_id("del-1") is True
        assert delete_debate_by_id("del-1") is False

        with open(temp_path, "r", encoding="utf-8") as f:
            remaining = json.load(f)
        assert len(remaining) == 1
        assert remaining[0]["id"] == "del-2"
        print("✓ Confirmed: delete_debate_by_id safely deletes specific records.")
        print("=== TEST 19 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_preset_topics():
    print("=== TEST 20: Preset Debate Topics ===")
    categories = get_preset_categories()
    assert isinstance(categories, list)
    assert "Artificial Intelligence" in categories
    assert "Society & Ethics" in categories
    assert "Science & Environment" in categories

    ai_topics = get_topics_for_category("Artificial Intelligence")
    assert len(ai_topics) >= 2
    assert all(isinstance(t, str) and len(t) > 0 for t in ai_topics)

    empty_topics = get_topics_for_category("NonExistentCategory")
    assert empty_topics == []
    print("✓ Confirmed: Preset topic categories and lists load cleanly.")
    print("=== TEST 20 PASSED ===\n")


def test_generate_debate_slug():
    print("=== TEST 21: Generate Debate Slug ===")
    assert generate_debate_slug("Should AI replace human programmers?") == "should-ai-replace-human-programmers"
    assert generate_debate_slug("AI: The Future? (Yes/No!)") == "ai-the-future-yes-no"
    
    slug_trunc = generate_debate_slug("This is a very long debate topic that exceeds twenty chars", max_length=20)
    assert len(slug_trunc) <= 20
    assert not slug_trunc.endswith("-")
    
    assert generate_debate_slug("") == "debate"
    assert generate_debate_slug("   ") == "debate"
    assert generate_debate_slug(None) == "debate"
    print("✓ Confirmed: generate_debate_slug outputs safe and clean slugs.")
    print("=== TEST 21 PASSED ===\n")


def test_backup_history():
    print("=== TEST 22: Backup History Utility ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    custom_backup = temp_path + ".bak"
    try:
        sample = [{"id": "b1", "topic": "Topic B1"}, {"id": "b2", "topic": "Topic B2"}]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(sample, f)

        backup_file = backup_history(dest_path=custom_backup)
        assert os.path.exists(backup_file)
        with open(backup_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert len(loaded) == 2
        assert loaded[0]["id"] == "b1"

        auto_backup = backup_history()
        assert os.path.exists(auto_backup)
        try:
            os.remove(auto_backup)
        except Exception:
            pass
        print("✓ Confirmed: backup_history creates valid backup copies of history.")
        print("=== TEST 22 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
        if os.path.exists(custom_backup):
            try:
                os.remove(custom_backup)
            except Exception:
                pass


def test_estimate_token_count():
    print("=== TEST 23: Approximate Token Estimation ===")
    assert estimate_token_count("") == 0
    assert estimate_token_count("   ") == 0
    assert estimate_token_count(None) == 0
    assert estimate_token_count("AI") == 1
    assert estimate_token_count("Hello world!") == 3

    orch = DebateOrchestrator(topic="Testing token metrics", total_rounds=1)
    orch.transcript.append({"speaker": "A", "round": 1, "text": "This is a clean speech with several words."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "Another speech with counter points here."})
    
    metrics = orch.get_speech_metrics()
    assert "tokens_a" in metrics
    assert "tokens_b" in metrics
    assert "total_tokens" in metrics
    assert metrics["tokens_a"] > 0
    assert metrics["tokens_b"] > 0
    assert metrics["total_tokens"] == metrics["tokens_a"] + metrics["tokens_b"]
    print("✓ Confirmed: Token estimation calculates sensible token counts.")
    print("=== TEST 23 PASSED ===\n")


def test_get_debater_stance():
    print("=== TEST 24: Get Debater Stance Utility ===")
    stance_a = get_debater_stance("A", "AI should be open source")
    stance_b = get_debater_stance("B", "AI should be open source")
    assert "FOR" in stance_a
    assert "AGAINST" in stance_b
    assert "AI should be open source" in stance_a
    
    assert get_debater_stance("a", "Topic") == get_debater_stance("A", "Topic")
    assert get_debater_stance("b", "Topic") == get_debater_stance("B", "Topic")
    
    try:
        get_debater_stance("C", "Topic")
        assert False, "Should raise ValueError for invalid speaker"
    except ValueError as e:
        assert "Invalid debater speaker" in str(e)

    orch = DebateOrchestrator(topic="Remote work is optimal", total_rounds=1)
    assert orch.get_stance("A") == get_debater_stance("A", "Remote work is optimal")
    print("✓ Confirmed: get_debater_stance returns accurate position descriptions.")
    print("=== TEST 24 PASSED ===\n")


def test_filter_debates_by_winner():
    print("=== TEST 25: Filter Debates By Winner ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    
    try:
        assert filter_debates_by_winner("A") == []
        assert filter_debates_by_winner("invalid") == []
        assert filter_debates_by_winner(None) == []

        mock_data = [
            {"id": "w1", "judge_winner": "A"},
            {"id": "w2", "judge_winner": "B"},
            {"id": "w3", "judge_winner": "A"},
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        res_a = filter_debates_by_winner("A")
        assert len(res_a) == 2
        assert res_a[0]["id"] == "w1"
        assert res_a[1]["id"] == "w3"

        res_b = filter_debates_by_winner("b")
        assert len(res_b) == 1
        assert res_b[0]["id"] == "w2"
        print("✓ Confirmed: filter_debates_by_winner accurately groups debate winners.")
        print("=== TEST 25 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_export_transcript_html():
    print("=== TEST 26: Export Transcript to HTML ===")
    orch = DebateOrchestrator(topic="Remote work is better than office work", total_rounds=1)
    empty_html = orch.export_transcript_html()
    assert "<!DOCTYPE html>" in empty_html
    assert "No arguments recorded yet." in empty_html
    assert "Remote work is better than office work" in empty_html

    orch.transcript.append({"speaker": "A", "round": 1, "text": "Remote work saves commute time."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "Office work fosters team bonding."})
    orch.revealed_verdict = {
        "winner": "A",
        "user_vote": "A",
        "agreed_with_ai": True,
        "reasoning": "Debater A had stronger time efficiency evidence."
    }
    full_html = orch.export_transcript_html()
    assert "<!DOCTYPE html>" in full_html
    assert "speaker-a" in full_html
    assert "speaker-b" in full_html
    assert "Remote work saves commute time." in full_html
    assert "Office work fosters team bonding." in full_html
    assert "Official Verdict" in full_html
    assert "Debater A had stronger time efficiency evidence." in full_html
    print("✓ Confirmed: HTML transcript export generates valid, styled HTML document.")
    print("=== TEST 26 PASSED ===\n")


def test_export_transcript_csv():
    print("=== TEST 27: Export Transcript to CSV ===")
    orch = DebateOrchestrator(topic="Cats make better pets than dogs", total_rounds=1)
    empty_csv = orch.export_transcript_csv()
    assert "round,speaker,stance,word_count,text" in empty_csv
    assert len(empty_csv.splitlines()) == 1

    orch.transcript.append({"speaker": "A", "round": 1, "text": "Cats are clean and quiet."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "Dogs provide loyal companionship and protection."})
    full_csv = orch.export_transcript_csv()
    lines = full_csv.splitlines()
    assert len(lines) == 3
    assert lines[0] == "round,speaker,stance,word_count,text"
    assert "1,A,FOR,5,Cats are clean and quiet." in lines[1]
    assert "1,B,AGAINST,6,Dogs provide loyal companionship and protection." in lines[2]
    print("✓ Confirmed: CSV transcript export generates clean tabular speech records.")
    print("=== TEST 27 PASSED ===\n")


def test_filter_debates_by_date():
    print("=== TEST 28: Filter Debates By Date ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    try:
        sample_records = [
            {"id": "d1", "timestamp": "2026-09-20T10:00:00+00:00", "topic": "Past Topic"},
            {"id": "d2", "timestamp": "2026-09-25T14:30:00+00:00", "topic": "Middle Topic"},
            {"id": "d3", "timestamp": "2026-10-01T09:15:00+00:00", "topic": "Current Topic"},
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(sample_records, f)

        all_res = filter_debates_by_date()
        assert len(all_res) == 3

        after_24 = filter_debates_by_date(start_date="2026-09-24")
        assert len(after_24) == 2
        assert [r["id"] for r in after_24] == ["d2", "d3"]

        before_26 = filter_debates_by_date(end_date="2026-09-26")
        assert len(before_26) == 2
        assert [r["id"] for r in before_26] == ["d1", "d2"]

        exact_range = filter_debates_by_date(start_date="2026-09-21", end_date="2026-09-30")
        assert len(exact_range) == 1
        assert exact_range[0]["id"] == "d2"

        print("✓ Confirmed: filter_debates_by_date correctly filters records by timestamp ranges.")
        print("=== TEST 28 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_calculate_lexical_diversity():
    print("=== TEST 29: Calculate Lexical Diversity ===")
    assert calculate_lexical_diversity("") == 0.0
    assert calculate_lexical_diversity("   ") == 0.0

    all_unique = "Cats are very clean"
    assert calculate_lexical_diversity(all_unique) == 1.0

    repeated = "Cats dogs Cats dogs"
    assert calculate_lexical_diversity(repeated) == 0.5

    orch = DebateOrchestrator(topic="Diversity check", total_rounds=1)
    orch.transcript.append({"speaker": "A", "round": 1, "text": "Clear logic wins debates."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "No no no no."})
    metrics = orch.get_speech_metrics()
    assert metrics["lexical_diversity_a"] == 1.0
    assert metrics["lexical_diversity_b"] == 0.25
    print("✓ Confirmed: Lexical diversity calculates accurate vocabulary richness ratios.")
    print("=== TEST 29 PASSED ===\n")


def test_search_preset_topics():
    print("=== TEST 30: Search Preset Topics ===")
    all_presets = search_preset_topics()
    assert len(all_presets) == 9

    ai_results = search_preset_topics("artificial intelligence")
    assert len(ai_results) == 3
    for r in ai_results:
        assert r["category"] == "Artificial Intelligence"

    ubi_results = search_preset_topics("basic income")
    assert len(ubi_results) == 1
    assert "universal basic income" in ubi_results[0]["topic"].lower()

    climate_results = search_preset_topics("climate")
    assert len(climate_results) == 1
    assert climate_results[0]["category"] == "Science & Environment"

    no_match = search_preset_topics("nonexistent xyz term")
    assert no_match == []

    print("✓ Confirmed: search_preset_topics accurately filters presets across categories.")
    print("=== TEST 30 PASSED ===\n")


def test_get_round_exchanges():
    print("=== TEST 31: Get Round Exchanges ===")
    orch = DebateOrchestrator(topic="Should college education be free?", total_rounds=2)
    assert orch.get_round_exchanges() == []

    orch.transcript.append({"speaker": "A", "round": 1, "text": "Education empowers youth."})
    orch.transcript.append({"speaker": "B", "round": 1, "text": "Free tuition strains public budgets."})
    orch.transcript.append({"speaker": "A", "round": 2, "text": "Higher education returns tax revenue long term."})
    orch.transcript.append({"speaker": "B", "round": 2, "text": "Vocational paths provide faster trade employment."})

    exchanges = orch.get_round_exchanges()
    assert len(exchanges) == 2
    assert exchanges[0]["round"] == 1
    assert exchanges[0]["debater_a"] == "Education empowers youth."
    assert exchanges[0]["debater_b"] == "Free tuition strains public budgets."
    assert exchanges[1]["round"] == 2
    assert exchanges[1]["debater_a"] == "Higher education returns tax revenue long term."
    assert exchanges[1]["debater_b"] == "Vocational paths provide faster trade employment."

    print("✓ Confirmed: get_round_exchanges pairs turn arguments cleanly by round.")
    print("=== TEST 31 PASSED ===\n")


def test_get_history_summary_report():
    print("=== TEST 32: Get History Summary Report ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    try:
        empty_rep = get_history_summary_report()
        assert empty_rep["total_debates"] == 0
        assert empty_rep["dominant_winner"] == "Tied"

        mock_data = [
            {"id": "1", "agreed": True, "user_vote": "A", "judge_winner": "A", "scores": {"A": {"total": 25}, "B": {"total": 20}}},
            {"id": "2", "agreed": False, "user_vote": "B", "judge_winner": "A", "scores": {"A": {"total": 24}, "B": {"total": 22}}},
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        rep = get_history_summary_report()
        assert rep["total_debates"] == 2
        assert rep["agreement_rate_pct"] == 50.0
        assert rep["judge_win_rate_a_pct"] == 100.0
        assert rep["judge_win_rate_b_pct"] == 0.0
        assert rep["dominant_winner"] == "Debater A"
        assert rep["score_margin"] == 3.5

        print("✓ Confirmed: get_history_summary_report provides accurate percentage summaries.")
        print("=== TEST 32 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_debate_duration_tracking():
    print("=== TEST 33: Debate Duration Tracking ===")
    orch = DebateOrchestrator(topic="Duration measurement test", total_rounds=1)
    assert orch.start_time is not None
    assert orch.end_time is None
    dur_initial = orch.get_duration_seconds()
    assert dur_initial >= 0.0

    orch._judge_verdict = {"winner": "A", "scores": {}, "reasoning": "Quick"}
    orch.submit_user_vote("A")
    assert orch.end_time is not None
    dur_final = orch.get_duration_seconds()
    assert dur_final >= dur_initial

    print("✓ Confirmed: Debate duration tracking records session timings accurately.")
    print("=== TEST 33 PASSED ===\n")


def test_get_winning_margin():
    print("=== TEST 34: Get Winning Margin ===")
    assert get_winning_margin({}) == 0
    assert get_winning_margin({"scores": {}}) == 0

    verdict_tied = {
        "scores": {
            "A": {"total": 24},
            "B": {"total": 24}
        }
    }
    assert get_winning_margin(verdict_tied) == 0

    verdict_diff = {
        "scores": {
            "A": {"total": 28},
            "B": {"total": 22}
        }
    }
    assert get_winning_margin(verdict_diff) == 6

    print("✓ Confirmed: get_winning_margin correctly calculates judge point differentials.")
    print("=== TEST 34 PASSED ===\n")


def test_validate_preset_topic():
    print("=== TEST 35: Validate Preset Topic ===")
    assert not validate_preset_topic("")
    assert not validate_preset_topic("Too short")
    assert not validate_preset_topic("   ")
    assert not validate_preset_topic("   !!!   ")
    assert not validate_preset_topic("a" * 201)

    assert validate_preset_topic("Should renewable energy replace coal entirely?")
    assert validate_preset_topic("Remote work is superior to in-office work.")

    print("✓ Confirmed: validate_preset_topic enforces clean topic quality standards.")
    print("=== TEST 35 PASSED ===\n")


def test_prune_history():
    print("=== TEST 36: Prune History Utility ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    try:
        sample_records = [
            {"id": "d1", "topic": "Oldest Topic 1"},
            {"id": "d2", "topic": "Older Topic 2"},
            {"id": "d3", "topic": "Recent Topic 3"},
            {"id": "d4", "topic": "Newest Topic 4"},
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(sample_records, f)

        # Prune to keep 2 newest without creating backup file
        removed = prune_history(keep_count=2, backup_first=False)
        assert removed == 2

        with open(temp_path, "r", encoding="utf-8") as f:
            kept = json.load(f)
        assert len(kept) == 2
        assert kept[0]["id"] == "d3"
        assert kept[1]["id"] == "d4"

        # Prune with keep_count greater than current length does nothing
        assert prune_history(keep_count=10, backup_first=False) == 0

        print("✓ Confirmed: prune_history safely retains newest records and removes older history.")
        print("=== TEST 36 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def test_calculate_readability_score():
    print("=== TEST 37: Calculate Readability Score ===")
    assert calculate_readability_score("") == 0.0
    assert calculate_readability_score("   ") == 0.0

    simple_text = "Cats are great pets. Dogs are loyal and friendly."
    complex_text = "Inordinately disproportionate socio-economic industrialization precipitates infrastructural repercussions."

    score_simple = calculate_readability_score(simple_text)
    score_complex = calculate_readability_score(complex_text)

    assert score_simple > score_complex
    assert 0.0 <= score_simple <= 100.0
    assert 0.0 <= score_complex <= 100.0

    orch = DebateOrchestrator(topic="Readability testing", total_rounds=1)
    orch.transcript.append({"speaker": "A", "round": 1, "text": simple_text})
    orch.transcript.append({"speaker": "B", "round": 1, "text": complex_text})
    metrics = orch.get_speech_metrics()
    assert metrics["readability_a"] == score_simple
    assert metrics["readability_b"] == score_complex

    print("✓ Confirmed: calculate_readability_score scores plain language higher than dense prose.")
    print("=== TEST 37 PASSED ===\n")


def test_export_history_csv():
    print("=== TEST 38: Export History to CSV ===")
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
        temp_path = tf.name
    orig_env = os.environ.get("DEBATR_HISTORY_FILE")
    os.environ["DEBATR_HISTORY_FILE"] = temp_path
    try:
        # Empty history
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump([], f)
        empty_csv = export_history_csv()
        assert "id,timestamp,topic,rounds,user_vote,judge_winner,agreed,score_a,score_b" in empty_csv
        assert len(empty_csv.splitlines()) == 1

        mock_data = [
            {
                "id": "h1",
                "timestamp": "2026-10-04T12:00:00+00:00",
                "topic": "AI Personhood",
                "rounds": 2,
                "user_vote": "A",
                "judge_winner": "A",
                "agreed": True,
                "scores": {"A": {"total": 26}, "B": {"total": 21}},
            }
        ]
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(mock_data, f)

        csv_out = export_history_csv()
        lines = csv_out.splitlines()
        assert len(lines) == 2
        assert "h1,2026-10-04T12:00:00+00:00,AI Personhood,2,A,A,True,26,21" in lines[1]

        # Test writing to file
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as cf:
            out_file = cf.name
        export_history_csv(output_path=out_file)
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "AI Personhood" in content
        if os.path.exists(out_file):
            os.remove(out_file)

        print("✓ Confirmed: export_history_csv exports all debate records in clean CSV format.")
        print("=== TEST 38 PASSED ===\n")
    finally:
        if orig_env is not None:
            os.environ["DEBATR_HISTORY_FILE"] = orig_env
        else:
            os.environ.pop("DEBATR_HISTORY_FILE", None)
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass









if __name__ == "__main__":
    test_mock_vote_reveal_ordering()
    test_history_stats_structure()
    test_transcript_formatting()
    test_debate_input_validation()
    test_parse_judge_json_edge_cases()
    test_get_debate_by_id()
    test_export_transcript_markdown()
    test_clear_history()
    test_history_stats_calculations()
    test_sanitize_topic()
    test_custom_model_override()
    test_speech_metrics()
    test_export_transcript_json()
    test_export_transcript_plain_text()
    test_debate_status_lifecycle()
    test_get_recent_debates()
    test_search_debates()
    test_delete_debate_by_id()
    test_preset_topics()
    test_generate_debate_slug()
    test_backup_history()
    test_estimate_token_count()
    test_get_debater_stance()
    test_filter_debates_by_winner()
    test_export_transcript_html()
    test_export_transcript_csv()
    test_filter_debates_by_date()
    test_calculate_lexical_diversity()
    test_search_preset_topics()
    test_get_round_exchanges()
    test_get_history_summary_report()
    test_debate_duration_tracking()
    test_get_winning_margin()
    test_validate_preset_topic()
    test_prune_history()
    test_calculate_readability_score()
    test_export_history_csv()
    
    run_live = "--live" in sys.argv or os.environ.get("RUN_LIVE_TESTS") == "1"
    if run_live:
        test_live_llm_debate()
    else:
        print("ℹ️ Skipping live LLM integration test. Run with 'python test_orchestrator.py --live' to run live tests.")









