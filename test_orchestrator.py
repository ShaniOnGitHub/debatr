import sys
import os
import tempfile
from orchestrator import DebateOrchestrator, get_history_stats, get_debate_by_id

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



if __name__ == "__main__":
    test_mock_vote_reveal_ordering()
    test_history_stats_structure()
    test_transcript_formatting()
    test_debate_input_validation()
    test_parse_judge_json_edge_cases()
    test_get_debate_by_id()
    test_export_transcript_markdown()
    
    run_live = "--live" in sys.argv or os.environ.get("RUN_LIVE_TESTS") == "1"
    if run_live:
        test_live_llm_debate()
    else:
        print("ℹ️ Skipping live LLM integration test. Run with 'python test_orchestrator.py --live' to run live tests.")







