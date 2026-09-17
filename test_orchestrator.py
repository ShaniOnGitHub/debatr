import sys
import os
from orchestrator import DebateOrchestrator, get_history_stats

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")


def test_mock_vote_reveal_ordering():
    print("\n=== TEST 1: Mock Vote/Reveal Ordering & Privacy ===")
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


if __name__ == "__main__":
    test_mock_vote_reveal_ordering()
    test_live_llm_debate()
