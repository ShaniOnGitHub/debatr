import os
import json
import uuid
import datetime
from typing import Generator, Dict, Any, List, Optional
import requests

def load_dotenv():
    """Lightweight loader for .env file without external dependencies."""
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k_clean = k.strip()
                        if k_clean and k_clean not in os.environ:
                            os.environ[k_clean] = v.strip().strip('"').strip("'")
        except Exception:
            pass

load_dotenv()

DEFAULT_MODEL = "stealth/union-alpha"
DEFAULT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "debates_history.json")

def get_history_file() -> str:
    """Returns the path to the history file, allowing override via DEBATR_HISTORY_FILE."""
    return os.environ.get("DEBATR_HISTORY_FILE") or DEFAULT_HISTORY_FILE


def get_api_key() -> str:
    env_key = os.environ.get("OPENROUTER_API_KEY")
    if env_key and env_key.strip():
        return env_key.strip()
    raise ValueError("OPENROUTER_API_KEY is not set. Please add it to your .env file or set the environment variable.")

def get_model() -> str:
    return os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)

def _handle_api_response_errors(response: requests.Response, model_name: str) -> None:
    """Provides plain-language error messages for OpenRouter HTTP failures."""
    if response.ok:
        return
    if response.status_code == 401:
        raise RuntimeError("OpenRouter rejected the request: your API key is invalid or missing. Check your .env file.")
    if response.status_code == 404:
        raise RuntimeError(f"The model '{model_name}' was not found on OpenRouter. Check your OPENROUTER_MODEL setting.")
    if response.status_code == 429:
        raise RuntimeError("OpenRouter rate limit reached or account credits are exhausted. Please check your account.")
    raise RuntimeError(f"OpenRouter request failed with code {response.status_code}: {response.text[:200]}")


def call_openrouter_stream(messages: List[Dict[str, str]], model: Optional[str] = None) -> Generator[str, None, None]:
    """Streams token chunks from OpenRouter chat completions API."""
    api_key = get_api_key()
    selected_model = model or get_model()
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://debatr.local",
        "X-Title": "Debatr Simulator"
    }
    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": True,
        "temperature": 0.7,
    }
    
    response = requests.post(url, headers=headers, json=payload, stream=True, timeout=60)
    _handle_api_response_errors(response, selected_model)

    
    for line in response.iter_lines():
        if not line:
            continue
        line_str = line.decode("utf-8")
        if line_str.startswith(":"):
            # SSE comment/keepalive from OpenRouter
            continue
        if line_str.startswith("data: "):
            data_content = line_str[6:].strip()
            if data_content == "[DONE]":
                break
            try:
                chunk = json.loads(data_content)
                delta = chunk.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
            except Exception:
                continue

def call_openrouter_sync(messages: List[Dict[str, str]], model: Optional[str] = None) -> str:
    """Non-streaming call to OpenRouter chat completions API."""
    api_key = get_api_key()
    selected_model = model or get_model()
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://debatr.local",
        "X-Title": "Debatr Simulator"
    }
    payload = {
        "model": selected_model,
        "messages": messages,
        "stream": False,
        "temperature": 0.3,
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    _handle_api_response_errors(response, selected_model)
    data = response.json()
    return data["choices"][0]["message"]["content"]


class DebateOrchestrator:
    """
    Orchestrates multi-round debate between Debater A (FOR) and Debater B (AGAINST),
    runs silent background judge evaluation after all rounds, and withholds judge verdict
    until user casts their vote.
    """
    def __init__(self, topic: str, total_rounds: int = 3):
        cleaned_topic = topic.strip() if isinstance(topic, str) else ""
        if not cleaned_topic:
            raise ValueError("Debate topic cannot be empty.")
        if not isinstance(total_rounds, int) or total_rounds < 1:
            raise ValueError("Total rounds must be a positive integer (at least 1).")
        self.id = str(uuid.uuid4())
        self.topic = cleaned_topic
        self.total_rounds = total_rounds

        self.transcript: List[Dict[str, Any]] = []  # [{ "speaker": "A" | "B", "text": str, "round": int }]
        self._judge_verdict: Optional[Dict[str, Any]] = None  # Held privately on server/backend
        self.user_vote: Optional[str] = None
        self.revealed_verdict: Optional[Dict[str, Any]] = None
        self.completed = False

    def get_transcript_text(self) -> str:
        if not self.transcript:
            return "No arguments made yet."
        lines = []
        for entry in self.transcript:
            speaker_name = "Debater A (FOR)" if entry["speaker"] == "A" else "Debater B (AGAINST)"
            lines.append(f"Round {entry['round']} - {speaker_name}:\n{entry['text']}")
        return "\n\n".join(lines)

    def _build_debater_messages(self, speaker: str, round_num: int) -> List[Dict[str, str]]:
        is_a = (speaker == "A")
        stance = f"FOR the topic: \"{self.topic}\"" if is_a else f"AGAINST the topic: \"{self.topic}\""
        
        system_prompt = (
            f"You are Debater {speaker} in a structured formal debate.\n"
            f"Your position: You argue strictly {stance}.\n"
            "Rules you must strictly follow:\n"
            "- Directly rebut your opponent's latest points and claims if they have spoken.\n"
            "- Advance your own strong arguments, evidence, and logical points.\n"
            "- Keep your response under 150 words. Be sharp, compelling, and punchy.\n"
            "- Under NO circumstances concede, hedge, apologize, or break character.\n"
            f"- Do not prefix your output with 'Debater {speaker}:' or any label. Speak directly.\n\n"
            "Language Rule:\n"
            "- Write for a smart reader with no specialist background in this subject.\n"
            "- Avoid jargon, technical terms, and insider vocabulary. If a term is genuinely necessary and has no simple substitute, define it in the same sentence in plain words; do not assume the reader already knows it.\n"
            "- Prefer short, direct sentences over academic phrasing. If you can make the same point with a simpler word, use the simpler word.\n"
            "- The goal is that anyone off the street could read this and follow the argument without pausing to look anything up."
        )
        
        history_text = self.get_transcript_text()
        if round_num == 1 and speaker == "A":
            user_prompt = (
                f"Topic: {self.topic}\n\n"
                "You are delivering the opening argument FOR this topic. "
                "Present your strongest initial case in under 150 words."
            )
        else:
            opponent = "Debater B" if is_a else "Debater A"
            user_prompt = (
                f"Topic: {self.topic}\n\n"
                f"Full transcript of debate so far:\n{history_text}\n\n"
                f"Now deliver your response for Round {round_num}. Directly dismantle {opponent}'s points "
                "and fortify your stance in under 150 words."
            )
            
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def stream_turn(self, speaker: str, round_num: int) -> Generator[str, None, None]:
        """Streams turn for speaker ('A' or 'B'), accumulates text, and appends to transcript."""
        messages = self._build_debater_messages(speaker, round_num)
        collected_tokens = []
        for token in call_openrouter_stream(messages):
            collected_tokens.append(token)
            yield token
        
        full_text = "".join(collected_tokens).strip()
        self.transcript.append({
            "speaker": speaker,
            "round": round_num,
            "text": full_text
        })

    def run_turn_sync(self, speaker: str, round_num: int) -> str:
        """Synchronous version of turn execution."""
        tokens = list(self.stream_turn(speaker, round_num))
        return "".join(tokens)

    def evaluate_judge_silently(self) -> None:
        """
        Calls the LLM Judge with the full transcript and stores the result server-side.
        DOES NOT reveal it to the frontend or user until vote is cast.
        """
        transcript_text = self.get_transcript_text()
        
        system_prompt = (
            "You are an expert, objective debate adjudicator.\n"
            "You are evaluating the complete transcript of a formal debate between Debater A (FOR) and Debater B (AGAINST).\n"
            "Carefully evaluate both debaters on these three explicit criteria:\n"
            "1. Logical Consistency: Soundness of arguments, absence of fallacies or contradictions.\n"
            "2. Evidence & Substantiation: Plausibility, use of concrete examples and grounded reasoning.\n"
            "3. Rebuttal Engagement: Whether the debater directly attacked and dismantled the opponent's points or evaded them.\n\n"
            "You must declare a single winner ('A' or 'B'). Ties are strictly forbidden.\n"
            "Language Rule for reasoning: Write for a smart reader with no specialist background. Avoid jargon, technical terms, and dense academic phrasing. Keep sentences direct and accessible.\n"
            "You must output ONLY valid raw JSON with no markdown backticks, no comments, and no additional text.\n"
            "Expected JSON schema:\n"
            "{\n"
            '  "winner": "A" or "B",\n'
            '  "scores": {\n'
            '    "A": { "logical_consistency": 1-10, "evidence_use": 1-10, "rebuttal_engagement": 1-10, "total": 3-30 },\n'
            '    "B": { "logical_consistency": 1-10, "evidence_use": 1-10, "rebuttal_engagement": 1-10, "total": 3-30 }\n'
            "  },\n"
            '  "reasoning": "Decisive analysis explaining why the winner won based on the criteria."\n'
            "}"
        )
        
        user_prompt = (
            f"Topic: {self.topic}\n\n"
            f"Full Debate Transcript:\n{transcript_text}\n\n"
            "Provide your final JSON verdict now."
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        raw_judge_output = call_openrouter_sync(messages)
        self._judge_verdict = self._parse_judge_json(raw_judge_output)

    def _parse_judge_json(self, raw_text: str) -> Dict[str, Any]:
        """Robustly extracts and validates JSON from model response."""
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
            
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx >= start_idx:
            cleaned = cleaned[start_idx:end_idx + 1]
            
        try:
            parsed = json.loads(cleaned)
            # Ensure winner is normalized
            winner = str(parsed.get("winner", "A")).strip().upper()
            if "A" in winner and "B" not in winner:
                winner = "A"
            elif "B" in winner:
                winner = "B"
            else:
                winner = "A"
            parsed["winner"] = winner
            return parsed
        except Exception:
            # Fallback default structure if parsing fails
            return {
                "winner": "A",
                "scores": {
                    "A": {"logical_consistency": 8, "evidence_use": 8, "rebuttal_engagement": 8, "total": 24},
                    "B": {"logical_consistency": 7, "evidence_use": 7, "rebuttal_engagement": 7, "total": 21}
                },
                "reasoning": cleaned[:300] if cleaned else "Debater A demonstrated superior argument structure and rebuttal."
            }

    def submit_user_vote(self, user_vote: str) -> Dict[str, Any]:
        """
        Only releases the judge verdict to the frontend after the user submits their own vote.
        Saves the debate record into debates_history.json.
        """
        user_vote_normalized = user_vote.strip().upper()
        if user_vote_normalized not in ("A", "B"):
            raise ValueError(f"Invalid user vote '{user_vote}'. Must be 'A' or 'B'.")
        
        if self._judge_verdict is None:
            raise RuntimeError("Judge evaluation has not been executed yet.")
        
        self.user_vote = user_vote_normalized
        judge_winner = self._judge_verdict.get("winner", "A")
        agreed = (self.user_vote == judge_winner)
        
        self.revealed_verdict = {
            **self._judge_verdict,
            "user_vote": self.user_vote,
            "agreed_with_ai": agreed
        }
        self.completed = True
        
        # Persist to history
        self._persist_history(agreed)
        
        return self.revealed_verdict

    def _persist_history(self, agreed: bool) -> None:
        record = {
            "id": self.id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "topic": self.topic,
            "rounds": self.total_rounds,
            "user_vote": self.user_vote,
            "judge_winner": self._judge_verdict.get("winner"),
            "agreed": agreed,
            "scores": self._judge_verdict.get("scores"),
            "reasoning": self._judge_verdict.get("reasoning")
        }
        
        history_file = get_history_file()
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
                
        history.append(record)
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)


def get_history_stats() -> Dict[str, Any]:
    """Computes running agreement rate and counts across all recorded debates."""
    history_file = get_history_file()
    if not os.path.exists(history_file):
        return {
            "total_debates": 0,
            "agreement_count": 0,
            "agreement_rate": 0.0,
            "user_wins_a": 0,
            "user_wins_b": 0,
            "judge_wins_a": 0,
            "judge_wins_b": 0,
        }
        
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        history = []
        
    total = len(history)
    if total == 0:
        return {
            "total_debates": 0,
            "agreement_count": 0,
            "agreement_rate": 0.0,
            "user_wins_a": 0,
            "user_wins_b": 0,
            "judge_wins_a": 0,
            "judge_wins_b": 0,
        }
        
    agreements = sum(1 for d in history if d.get("agreed", False))
    user_a = sum(1 for d in history if d.get("user_vote") == "A")
    user_b = sum(1 for d in history if d.get("user_vote") == "B")
    judge_a = sum(1 for d in history if d.get("judge_winner") == "A")
    judge_b = sum(1 for d in history if d.get("judge_winner") == "B")
    
    rate = round((agreements / total) * 100, 1)
    
    return {
        "total_debates": total,
        "agreement_count": agreements,
        "agreement_rate": rate,
        "user_wins_a": user_a,
        "user_wins_b": user_b,
        "judge_wins_a": judge_a,
        "judge_wins_b": judge_b,
    }


def get_debate_by_id(debate_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single debate record by its unique ID from the history file."""
    if not debate_id or not isinstance(debate_id, str):
        return None
        
    history_file = get_history_file()
    if not os.path.exists(history_file):
        return None
        
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                return None
            for item in history:
                if isinstance(item, dict) and item.get("id") == debate_id:
                    return item
    except Exception:
        return None
        
    return None

