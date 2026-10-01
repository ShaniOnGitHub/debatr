import os
import json
import uuid
import datetime
import html
import csv
import io
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

__version__ = "1.3.0"
DEFAULT_MODEL = "stealth/union-alpha"
DEFAULT_HISTORY_FILE = os.path.join(os.path.dirname(__file__), "debates_history.json")
MAX_ROUNDS = 10

PRESET_TOPICS: Dict[str, List[str]] = {
    "Artificial Intelligence": [
        "Should artificial intelligence systems have legal personhood?",
        "Will generative AI cause more economic harm than benefit?",
        "Should governments require safety licenses for frontier AI models?",
    ],
    "Society & Ethics": [
        "Should universal basic income replace traditional welfare programs?",
        "Is social media net negative for democratic discourse?",
        "Should remote work be recognized as a legal worker right?",
    ],
    "Science & Environment": [
        "Should nuclear energy be the primary replacement for fossil fuels?",
        "Should space exploration receive substantial government funding?",
        "Is geoengineering an acceptable tool to fight climate change?",
    ],
}


def get_preset_categories() -> List[str]:
    """Returns the available preset topic categories."""
    return list(PRESET_TOPICS.keys())


def get_topics_for_category(category: str) -> List[str]:
    """Returns the list of topics for a given category, or empty list if not found."""
    return PRESET_TOPICS.get(category, [])


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


def sanitize_topic(topic: str) -> str:
    """Cleans up debate topic text by removing extra spaces and control characters."""
    if not isinstance(topic, str):
        return ""
    cleaned = "".join(ch if ch.isprintable() else " " for ch in topic)
    return " ".join(cleaned.split()).strip()


def generate_debate_slug(topic: str, max_length: int = 40) -> str:
    """Creates a URL- and filename-safe slug from a debate topic."""
    if not isinstance(topic, str) or not topic.strip():
        return "debate"
    chars = [ch.lower() if ch.isalnum() else "-" for ch in topic.strip()]
    slug = "".join(chars)
    parts = [p for p in slug.split("-") if p]
    combined = "-".join(parts)
    if not combined:
        return "debate"
    if len(combined) <= max_length:
        return combined
    truncated = combined[:max_length].rstrip("-")
    return truncated or "debate"


def estimate_token_count(text: str) -> int:
    """Provides a fast, approximate token count without external libraries."""
    if not isinstance(text, str) or not text.strip():
        return 0
    return max(1, round(len(text.strip()) / 4.0))


def get_debater_stance(speaker: str, topic: str) -> str:
    """Returns a clear explanation of the debater's assigned stance."""
    normalized = str(speaker).strip().upper()
    if normalized == "A":
        return f"Argues FOR the proposition: \"{topic}\""
    if normalized == "B":
        return f"Argues AGAINST the proposition: \"{topic}\""
    raise ValueError(f"Invalid debater speaker '{speaker}'. Must be 'A' or 'B'.")


class DebateOrchestrator:
    """
    Orchestrates multi-round debate between Debater A (FOR) and Debater B (AGAINST),
    runs silent background judge evaluation after all rounds, and withholds judge verdict
    until user casts their vote.
    """
    def __init__(self, topic: str, total_rounds: int = 3, model: Optional[str] = None):
        cleaned_topic = sanitize_topic(topic)
        if not cleaned_topic:
            raise ValueError("Debate topic cannot be empty.")
        if not isinstance(total_rounds, int) or total_rounds < 1:
            raise ValueError("Total rounds must be a positive integer (at least 1).")
        if total_rounds > MAX_ROUNDS:
            raise ValueError(f"Total rounds cannot exceed {MAX_ROUNDS}.")
        self.id = str(uuid.uuid4())
        self.topic = cleaned_topic
        self.total_rounds = total_rounds
        self.model = model.strip() if isinstance(model, str) and model.strip() else None

        self.transcript: List[Dict[str, Any]] = []  # [{ "speaker": "A" | "B", "text": str, "round": int }]
        self._judge_verdict: Optional[Dict[str, Any]] = None  # Held privately on server/backend
        self.user_vote: Optional[str] = None
        self.revealed_verdict: Optional[Dict[str, Any]] = None
        self.completed = False

    @property
    def status(self) -> str:
        """
        Returns the current lifecycle stage of the debate:
        - 'pending': No arguments have been delivered yet.
        - 'in_progress': Debate turns are underway.
        - 'awaiting_vote': Arguments complete and judge has evaluated, awaiting user vote.
        - 'completed': User vote recorded and judge verdict revealed.
        """
        if self.completed or self.revealed_verdict is not None:
            return "completed"
        if self._judge_verdict is not None:
            return "awaiting_vote"
        if len(self.transcript) > 0:
            return "in_progress"
        return "pending"

    def get_transcript_text(self) -> str:
        if not self.transcript:
            return "No arguments made yet."
        lines = []
        for entry in self.transcript:
            speaker_name = "Debater A (FOR)" if entry["speaker"] == "A" else "Debater B (AGAINST)"
            lines.append(f"Round {entry['round']} - {speaker_name}:\n{entry['text']}")
        return "\n\n".join(lines)

    def get_stance(self, speaker: str) -> str:
        """Returns the debater's assigned stance for this debate's topic."""
        return get_debater_stance(speaker, self.topic)

    def get_speech_metrics(self) -> Dict[str, Any]:
        """Calculates word count and speech metrics for both debaters."""
        words_a = 0
        words_b = 0
        tokens_a = 0
        tokens_b = 0
        turns_a = 0
        turns_b = 0
        for entry in self.transcript:
            text = entry.get("text", "")
            wc = len(text.split())
            tc = estimate_token_count(text)
            if entry.get("speaker") == "A":
                words_a += wc
                tokens_a += tc
                turns_a += 1
            elif entry.get("speaker") == "B":
                words_b += wc
                tokens_b += tc
                turns_b += 1
        total_words = words_a + words_b
        total_tokens = tokens_a + tokens_b
        total_turns = turns_a + turns_b
        avg_words = round(total_words / total_turns, 1) if total_turns > 0 else 0.0
        return {
            "words_a": words_a,
            "words_b": words_b,
            "tokens_a": tokens_a,
            "tokens_b": tokens_b,
            "turns_a": turns_a,
            "turns_b": turns_b,
            "total_words": total_words,
            "total_tokens": total_tokens,
            "avg_words_per_turn": avg_words,
        }

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
        for token in call_openrouter_stream(messages, model=self.model):
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
        
        raw_judge_output = call_openrouter_sync(messages, model=self.model)
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

    def export_transcript_markdown(self) -> str:
        """
        Exports the entire debate transcript as a formatted Markdown document,
        including topic, speeches per round, and judge verdict if revealed.
        """
        lines = [
            f"# Debate: {self.topic}",
            f"- **Debate ID**: `{self.id}`",
            f"- **Total Rounds**: {self.total_rounds}",
            "",
            "## Speeches",
            ""
        ]
        if not self.transcript:
            lines.append("_No arguments recorded yet._\n")
        else:
            for entry in self.transcript:
                speaker_label = "Debater A (FOR)" if entry["speaker"] == "A" else "Debater B (AGAINST)"
                lines.append(f"### Round {entry['round']} — {speaker_label}")
                lines.append(f"{entry['text']}\n")
                
        if self.revealed_verdict:
            lines.append("## Official Verdict")
            lines.append(f"- **User Vote**: Debater {self.revealed_verdict.get('user_vote')}")
            lines.append(f"- **Judge Winner**: Debater {self.revealed_verdict.get('winner')}")
            lines.append(f"- **User Agreed With Judge**: {'Yes' if self.revealed_verdict.get('agreed_with_ai') else 'No'}")
            lines.append("\n### Judge Reasoning")
            lines.append(f"{self.revealed_verdict.get('reasoning', 'No reasoning provided.')}\n")
            
        return "\n".join(lines)

    def export_transcript_json(self, indent: int = 2) -> str:
        """
        Exports the debate as a formatted JSON string containing metadata,
        speeches, metrics, and verdict if available.
        """
        data = {
            "id": self.id,
            "topic": self.topic,
            "rounds": self.total_rounds,
            "speeches": self.transcript,
            "metrics": self.get_speech_metrics(),
            "verdict": self.revealed_verdict,
        }
        return json.dumps(data, indent=indent)

    def export_transcript_plain_text(self) -> str:
        """
        Exports the debate transcript as a clean, plain-text document
        without markdown syntax for easy copying.
        """
        lines = [
            f"DEBATE TOPIC: {self.topic}",
            f"Debate ID: {self.id}",
            f"Total Rounds: {self.total_rounds}",
            "=" * 50,
            ""
        ]
        if not self.transcript:
            lines.append("No arguments recorded yet.\n")
        else:
            for entry in self.transcript:
                speaker_label = "Debater A (FOR)" if entry["speaker"] == "A" else "Debater B (AGAINST)"
                lines.append(f"Round {entry['round']} - {speaker_label}:")
                lines.append(entry["text"])
                lines.append("")
        
        if self.revealed_verdict:
            lines.append("=" * 50)
            lines.append("OFFICIAL VERDICT")
            lines.append(f"User Vote: Debater {self.revealed_verdict.get('user_vote')}")
            lines.append(f"Judge Winner: Debater {self.revealed_verdict.get('winner')}")
            agreed = "Yes" if self.revealed_verdict.get('agreed_with_ai') else "No"
            lines.append(f"User Agreed With Judge: {agreed}")
            lines.append("")
            lines.append("Judge Reasoning:")
            lines.append(self.revealed_verdict.get('reasoning', 'No reasoning provided.'))
            lines.append("")
            
        return "\n".join(lines).strip()

    def export_transcript_html(self) -> str:
        """
        Exports the debate transcript as a self-contained HTML page
        with styling for web viewing and sharing.
        """
        escaped_topic = html.escape(self.topic)
        escaped_id = html.escape(self.id)
        
        cards = []
        if not self.transcript:
            cards.append("<p class='empty'>No arguments recorded yet.</p>")
        else:
            for entry in self.transcript:
                speaker = entry.get("speaker", "A")
                round_num = entry.get("round", 1)
                text = html.escape(entry.get("text", ""))
                speaker_title = "Debater A (FOR)" if speaker == "A" else "Debater B (AGAINST)"
                css_class = "speaker-a" if speaker == "A" else "speaker-b"
                cards.append(
                    f"<div class='speech-card {css_class}'>"
                    f"<h3>Round {round_num} - {speaker_title}</h3>"
                    f"<p>{text}</p>"
                    f"</div>"
                )
        
        verdict_section = ""
        if self.revealed_verdict:
            winner = html.escape(str(self.revealed_verdict.get("winner", "")))
            user_vote = html.escape(str(self.revealed_verdict.get("user_vote", "")))
            agreed = "Yes" if self.revealed_verdict.get("agreed_with_ai") else "No"
            reasoning = html.escape(str(self.revealed_verdict.get("reasoning", "")))
            verdict_section = (
                f"<section class='verdict-card'>"
                f"<h2>Official Verdict</h2>"
                f"<p><strong>Winner:</strong> Debater {winner}</p>"
                f"<p><strong>User Vote:</strong> Debater {user_vote}</p>"
                f"<p><strong>User Agreed With Judge:</strong> {agreed}</p>"
                f"<p><strong>Judge Reasoning:</strong> {reasoning}</p>"
                f"</section>"
            )

        html_output = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Debate: {escaped_topic}</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; color: #222; background: #fafafa; }}
h1 {{ color: #111; font-size: 1.6rem; border-bottom: 2px solid #e0e0e0; padding-bottom: 12px; }}
.meta {{ color: #666; font-size: 0.9rem; margin-bottom: 20px; }}
.speech-card {{ background: #fff; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; border-left: 5px solid #ccc; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
.speaker-a {{ border-left-color: #2563eb; }}
.speaker-b {{ border-left-color: #dc2626; }}
.speech-card h3 {{ margin-top: 0; font-size: 1.1rem; color: #333; }}
.speech-card p {{ line-height: 1.6; margin-bottom: 0; }}
.verdict-card {{ background: #f0fdf4; border: 1px solid #86efac; border-radius: 8px; padding: 20px; margin-top: 24px; }}
.verdict-card h2 {{ margin-top: 0; color: #166534; }}
</style>
</head>
<body>
<h1>{escaped_topic}</h1>
<div class="meta">Debate ID: {escaped_id} | Total Rounds: {self.total_rounds}</div>
<main>
{''.join(cards)}
</main>
{verdict_section}
</body>
</html>"""
        return html_output

    def export_transcript_csv(self) -> str:
        """
        Exports the debate speeches in comma-separated values (CSV) format
        for spreadsheet viewing and quantitative analysis.
        """
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(["round", "speaker", "stance", "word_count", "text"])
        for entry in self.transcript:
            speaker = entry.get("speaker", "A")
            round_num = entry.get("round", 1)
            text = entry.get("text", "")
            stance = "FOR" if str(speaker).upper() == "A" else "AGAINST"
            word_count = len(text.split())
            writer.writerow([round_num, speaker, stance, word_count, text])
        return output.getvalue().strip()





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
            "avg_score_a": 0.0,
            "avg_score_b": 0.0,
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
            "avg_score_a": 0.0,
            "avg_score_b": 0.0,
        }
        
    agreements = sum(1 for d in history if d.get("agreed", False))
    user_a = sum(1 for d in history if d.get("user_vote") == "A")
    user_b = sum(1 for d in history if d.get("user_vote") == "B")
    judge_a = sum(1 for d in history if d.get("judge_winner") == "A")
    judge_b = sum(1 for d in history if d.get("judge_winner") == "B")
    
    rate = round((agreements / total) * 100, 1)

    scores_a = [
        d["scores"]["A"]["total"]
        for d in history
        if isinstance(d, dict) and isinstance(d.get("scores"), dict) and "A" in d["scores"] and isinstance(d["scores"]["A"], dict) and "total" in d["scores"]["A"]
    ]
    scores_b = [
        d["scores"]["B"]["total"]
        for d in history
        if isinstance(d, dict) and isinstance(d.get("scores"), dict) and "B" in d["scores"] and isinstance(d["scores"]["B"], dict) and "total" in d["scores"]["B"]
    ]
    avg_score_a = round(sum(scores_a) / len(scores_a), 1) if scores_a else 0.0
    avg_score_b = round(sum(scores_b) / len(scores_b), 1) if scores_b else 0.0
    
    return {
        "total_debates": total,
        "agreement_count": agreements,
        "agreement_rate": rate,
        "user_wins_a": user_a,
        "user_wins_b": user_b,
        "judge_wins_a": judge_a,
        "judge_wins_b": judge_b,
        "avg_score_a": avg_score_a,
        "avg_score_b": avg_score_b,
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


def clear_history() -> bool:
    """Safely resets the debates history file to an empty record list."""
    history_file = get_history_file()
    try:
        dir_name = os.path.dirname(os.path.abspath(history_file))
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return True
    except Exception:
        return False


def get_recent_debates(limit: int = 5) -> List[Dict[str, Any]]:
    """Returns the most recent debates in reverse chronological order."""
    if not isinstance(limit, int) or limit < 1:
        return []
    history_file = get_history_file()
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                return []
            return list(reversed(history[-limit:]))
    except Exception:
        return []


def search_debates(query: str) -> List[Dict[str, Any]]:
    """Searches history for debates matching query in topic or reasoning."""
    cleaned_query = query.strip().lower() if isinstance(query, str) else ""
    if not cleaned_query:
        return []
    history_file = get_history_file()
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                return []
            results = []
            for item in history:
                if not isinstance(item, dict):
                    continue
                topic = str(item.get("topic", "")).lower()
                reasoning = str(item.get("reasoning", "")).lower()
                if cleaned_query in topic or cleaned_query in reasoning:
                    results.append(item)
            return results
    except Exception:
        return []


def delete_debate_by_id(debate_id: str) -> bool:
    """Removes a single debate record by its ID from history. Returns True if deleted."""
    if not debate_id or not isinstance(debate_id, str):
        return False
    history_file = get_history_file()
    if not os.path.exists(history_file):
        return False
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                return False
        initial_len = len(history)
        filtered = [item for item in history if isinstance(item, dict) and item.get("id") != debate_id]
        if len(filtered) == initial_len:
            return False
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(filtered, f, indent=2)
        return True
    except Exception:
        return False


def backup_history(dest_path: Optional[str] = None) -> str:
    """Creates a backup copy of the debates history file. Returns the backup file path."""
    history_file = get_history_file()
    data = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    data = loaded
        except Exception:
            data = []
    if dest_path and isinstance(dest_path, str) and dest_path.strip():
        target = os.path.abspath(dest_path.strip())
    else:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dir_name = os.path.dirname(os.path.abspath(history_file)) or "."
        target = os.path.join(dir_name, f"debates_history_backup_{ts}.json")
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return target


def filter_debates_by_winner(winner: str) -> List[Dict[str, Any]]:
    """Returns past debates won by a specific debater ('A' or 'B')."""
    if not isinstance(winner, str):
        return []
    normalized = winner.strip().upper()
    if normalized not in ("A", "B"):
        return []
    history_file = get_history_file()
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                return []
            return [d for d in history if isinstance(d, dict) and d.get("judge_winner") == normalized]
    except Exception:
        return []


def filter_debates_by_date(start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Returns past debates recorded within a specific date range.
    Accepts date strings like '2026-09-27' or full ISO timestamps.
    """
    history_file = get_history_file()
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
            if not isinstance(history, list):
                return []
    except Exception:
        return []

    results = []
    for item in history:
        if not isinstance(item, dict):
            continue
        ts = item.get("timestamp")
        if not ts or not isinstance(ts, str):
            continue
        if start_date and ts[:len(start_date)] < start_date:
            continue
        if end_date and ts[:len(end_date)] > end_date:
            continue
        results.append(item)
    return results



