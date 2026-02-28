# ⚡ Prompt Validator

AI-powered prompt validator that checks prompts against **4 validation rules** and generates production-ready fixes using Groq LLM (Llama 3.1).

## Validation Rules

| # | Rule | Description |
|---|------|-------------|
| 1 | **Redundancy** | Flags repetitive phrases and unnecessarily verbose wording |
| 2 | **Contradiction** | Detects conflicting requirements or instructions |
| 3 | **Missing Section** | Ensures Task, Success Criteria, Examples, and CoT/TOT sections exist |
| 4 | **Prohibited Content** | Catches PII (names, emails, phones) and secrets (API keys, passwords) |

## Features

- **Web UI** — Clean, modern interface with dark/light theme
- **Score System** — 0-10 quality score with weighted deductions
- **Auto-Fix** — LLM-generated corrected prompts with proper structure
- **Report Export** — Download JSON validation reports
- **CLI Tool** — Batch validate prompt files from the command line
- **API** — RESTful FastAPI endpoints (`POST /api/validate`)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install -e .
```

### 2. Set Environment Variable

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com).

### 3. Run Locally (Web UI)

```bash
uvicorn api.index:app --reload --port 8000
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### 4. Run CLI

```bash
prompt-validator sample_prompts/ --auto-fix --output report.json
```

## Deploy to Vercel

### One-Click Deploy

1. Push this repo to GitHub
2. Go to [vercel.com/new](https://vercel.com/new) and import the repo
3. Add environment variable: `GROQ_API_KEY` = your key
4. Click **Deploy**

### Manual Deploy

```bash
npm i -g vercel
vercel --prod
```

Set the `GROQ_API_KEY` environment variable in the Vercel dashboard under **Settings → Environment Variables**.

## API Reference

### `POST /api/validate`

**Request:**
```json
{
  "prompt": "Your prompt text here",
  "api_key": "gsk_... (optional, uses server key if omitted)"
}
```

**Response:**
```json
{
  "status": "success",
  "score": 7.0,
  "issues": [
    {
      "issue_type": "Redundancy",
      "description": "Repeated phrasing detected.",
      "suggestion": "Remove duplicate sentence."
    }
  ],
  "fixed_prompt": "### Task\n...",
  "summary": { "total_issues": 1, "categories": { "Redundancy": 1 } },
  "original_prompt": "Your prompt text here"
}
```

### `GET /api/health`

Returns service status and model info.

## Project Structure

```
├── api/
│   └── index.py            # FastAPI serverless function (Vercel)
├── public/
│   └── index.html          # Web UI (static)
├── src/prompt_validator/
│   ├── main.py             # CLI entry point
│   ├── validator.py        # Core validation logic
│   ├── llm_handler.py      # Groq LLM integration
│   ├── schemas.py          # Pydantic models
│   └── utils.py            # Report generation
├── tests/
│   └── test_validator.py   # Unit tests
├── sample_prompts/         # Example prompt files
├── vercel.json             # Vercel deployment config
├── requirements.txt        # Python dependencies
└── setup.py                # Package setup (CLI)
```

## Running Tests

```bash
pytest tests/ -v
```

## Tech Stack

- **Backend:** FastAPI, LangChain, Groq (Llama 3.1)
- **Frontend:** Vanilla HTML/CSS/JS (no build step)
- **Deployment:** Vercel (Python serverless + static files)
- **CLI:** Click, Rich