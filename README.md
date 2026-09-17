# ⚔️ Debatr — AI Debate Simulator

**Debatr** is an interactive debate web app where two AI debaters argue opposing sides of any proposition in real time. An impartial AI judge silently evaluates the entire debate in the background, keeping its score locked away until **you** cast your vote for the winner.

---

## ✨ Features

- **Multi-Round AI Debates**: Debater A argues **FOR** the topic; Debater B argues **AGAINST**. Both engage with each other's points, adhere to strict constraints (<150 words), and follow clear language guidelines (no jargon, accessible to everyone).
- **Live Word-by-Word Streaming**: Speeches stream dynamically into clean, modern chat bubbles.
- **The Secret AI Judge**: The judge automatically scores the debate on *Logical Consistency*, *Evidence & Substantiation*, and *Rebuttal Engagement*. The verdict is strictly kept confidential until the user votes.
- **Vote & Reveal**: Cast your ballot to unlock the judge's score card, criteria breakdown, and analytical reasoning.
- **Cumulative Agreement Rate**: Tracks your alignment with the AI judge across all debates.
- **Minimal, Modern UI**: Built with Streamlit with an in-page configuration panel, preset topics, and a live statistics banner.

---

## 🛠️ Architecture

```
User Input (Topic + Rounds)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              Debate Orchestrator (Backend)              │
│                                                         │
│  Round 1..N:                                            │
│    Debater A (FOR)     ───► Stream tokens to Frontend   │
│    Debater B (AGAINST) ───► Stream tokens to Frontend   │
│                                                         │
│  After All Rounds:                                      │
│    AI Judge Evaluates  ───► Verdict LOCKED in Backend   │
│                                                         │
│  User Submits Vote:                                     │
│    Unlocks Verdict     ───► Reveal Scores & Reasoning   │
│    Updates History     ───► Persists to debates_history │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/ShaniOnGitHub/debatr.git
cd debatr
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
Copy `.env.example` to `.env` and provide your OpenRouter API key:
```bash
cp .env.example .env
```
Inside `.env`:
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=stealth/union-alpha
```

### 4. Launch the application
```bash
streamlit run app.py
```
Open your browser at `http://localhost:8501`.

---

## 🧪 Running Tests

Debatr includes an automated test suite that verifies turn execution, verdict privacy, and vote reveal mechanics without needing a browser:

```bash
python test_orchestrator.py
```

---

## 📄 License

MIT License. Built for experimenters, debaters, and AI enthusiasts.
