import sys
import os
import tempfile
from orchestrator import DebateOrchestrator, get_history_stats

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


if __name__ == "__main__":
    test_mock_vote_reveal_ordering()
    test_history_stats_structure()
    test_transcript_formatting()
    test_debate_input_validation()
    test_parse_judge_json_edge_cases()
    
    run_live = "--live" in sys.argv or os.environ.get("RUN_LIVE_TESTS") == "1"
    if run_live:
        test_live_llm_debate()
    else:
        print("ℹ️ Skipping live LLM integration test. Run with 'python test_orchestrator.py --live' to run live tests.")





