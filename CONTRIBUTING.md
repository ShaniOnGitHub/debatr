# Contributing to Debatr

Thank you for your interest in improving Debatr! We welcome contributions of all kinds, including bug reports, documentation improvements, and new features.

---

## 🛠️ Getting Started

1. **Fork and Clone**
   ```bash
   git clone https://github.com/ShaniOnGitHub/debatr.git
   cd debatr
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Up Environment Variables**
   ```bash
   cp .env.example .env
   ```
   Add your OpenRouter API key and preferred model name to `.env`.

---

## 🧪 Testing

Always make sure all tests pass before opening a pull request.

- **Run standard unit tests (fast, offline, no API key needed):**
  ```bash
  python test_orchestrator.py
  ```

- **Run live integration tests (calls OpenRouter live models):**
  ```bash
  python test_orchestrator.py --live
  ```

---

## 📝 Writing Clear Code and Text

Please follow these guidelines:
- **Write for everyone**: Avoid technical jargon or insider words. If a term is required, explain it in the same sentence in simple terms.
- **Keep changes focused**: Only change what is necessary for your feature or bug fix.
- **Add tests**: When adding a new capability, include a matching unit test.

---

## 🚀 Submitting a Pull Request

1. Create a feature branch: `git checkout -b feature/my-new-feature`
2. Commit your changes with clear, descriptive commit messages.
3. Push to your branch: `git push origin feature/my-new-feature`
4. Open a Pull Request on GitHub describing what your change does.
