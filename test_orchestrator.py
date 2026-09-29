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
    generate_debate_slug,
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
    
    run_live = "--live" in sys.argv or os.environ.get("RUN_LIVE_TESTS") == "1"
    if run_live:
        test_live_llm_debate()
    else:
        print("ℹ️ Skipping live LLM integration test. Run with 'python test_orchestrator.py --live' to run live tests.")









