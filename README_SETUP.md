# Setup Instructions for Task3 Labeling

## 1. Clone Repository

```bash
git clone <repo-url>
cd automatic-citation-checking
```

## 2. Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# OR
venv\Scripts\activate  # On Windows

# Install dependencies
pip install -r requirements.txt
```

## 3. Configure API Keys

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and add your API keys
# vim .env
# OR
# nano .env
# OR use any text editor
```

**Required API Keys:**
- `GOOGLE_AI_API_KEY` - Get from https://ai.google.dev/
- `GROQ_API_KEY` - Get from https://console.groq.com/
- `HF_API_KEY` - Get from https://huggingface.co/settings/tokens

## 4. Run Labeling Scripts

```bash
# For Gemini (Google AI)
python label_task3_gemini.py train

# For Groq
python label_task3_groq.py train

# For HuggingFace
python label_task3_hf.py train

# For Ollama (local, no API key needed)
python label_task3_ollama.py train
```

## Available Splits

- `train` - Training set (~55k files)
- `val` - Validation set (3k files)
- `test_gold_500` - Gold test set (500 files) ✅ DONE
- `test_silver_2500` - Silver test set (2.5k files)

## Notes

- All scripts use relative paths, so they work on any machine
- Data is in `data_outputs/task3/`
- Progress is saved automatically (can resume if interrupted)
- Check `.env.example` for reference
