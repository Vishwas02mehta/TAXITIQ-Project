"""
create_benchmark_file.py — Generates clean question files for manual LLM baseline testing.
"""

import json
import os

BENCHMARK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "benchmark_questions_v2.json")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "llm_baseline")


def main() -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} benchmark questions.")

    prompt_header = (
        "Answer the following Indian income tax law questions based only on "
        "your internal knowledge. Do not browse the web or use external tools. "
        "If you are uncertain, answer honestly rather than inventing legal provisions.\n\n"
        "FORMAT: For each question, write your answer starting with the question number "
        "(e.g., Q001: Your answer here). Keep answers in 1-3 sentences. "
        "Cite the relevant section number if you know it.\n\n"
        + "=" * 70 + "\n\n"
    )

    # ── 1. Single prompt file (all 230 questions) ──────────────────
    full_text = prompt_header
    for q in questions:
        full_text += q["question_id"] + ": " + q["question"] + "\n\n"

    full_path = os.path.join(OUTPUT_DIR, "llm_benchmark_questions.txt")
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"  Created: {full_path}")

    # ── 2. Batched files (50 questions each) ───────────────────────
    batch_size = 50
    for batch_num, i in enumerate(range(0, len(questions), batch_size), start=1):
        batch = questions[i:i + batch_size]
        batch_text = prompt_header
        for q in batch:
            batch_text += q["question_id"] + ": " + q["question"] + "\n\n"

        batch_path = os.path.join(OUTPUT_DIR, f"questions_batch_{batch_num}.txt")
        with open(batch_path, "w", encoding="utf-8") as f:
            f.write(batch_text)
        print(f"  Created: {batch_path} ({len(batch)} questions)")

    # ── 3. Answer template JSON ────────────────────────────────────
    template = {
        "_instructions": (
            "Fill in the 'raw_answer' field for each question with the LLM's response. "
            "Set 'model_name' to the model you used (e.g., 'GPT-4.1', 'Claude Sonnet 4', "
            "'Gemini 2.5 Pro'). Save as a separate file per model."
        ),
        "model_name": "MODEL_NAME_HERE",
        "provider": "PROVIDER_HERE",
        "timestamp": "YYYY-MM-DDTHH:MM:SS",
        "answers": []
    }

    for q in questions:
        template["answers"].append({
            "question_id": q["question_id"],
            "question": q["question"],
            "raw_answer": ""
        })

    template_path = os.path.join(OUTPUT_DIR, "llm_answer_template.json")
    with open(template_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    print(f"  Created: {template_path}")

    # ── 4. Instructions README ─────────────────────────────────────
    readme = """# LLM Baseline Benchmark — Instructions

## What This Is
230 Indian income tax law questions from the TAXITIQ v2 benchmark.
Goal: Test how well standalone LLMs answer WITHOUT RAG/retrieval.

## How To Use

### Step 1: Send Questions to Each LLM
- Open the web version of the LLM (ChatGPT, Claude, Gemini, etc.)
- Copy-paste from `llm_benchmark_questions.txt` (all 230 at once)
- OR use batch files (`questions_batch_1.txt` through `questions_batch_5.txt`)

### Step 2: Save the Answers
**Option A (Easiest):** Save the LLM's full response as plain text:
```
answers_gpt4.1.txt
answers_claude_sonnet_4.txt
answers_gemini_2.5_pro.txt
```
The evaluator will parse Q001-Q230 automatically from the text.

**Option B (Structured):** Copy `llm_answer_template.json`, fill in answers.

### Step 3: Place Answer Files Here
Put all answer files in this `llm_baseline/` folder.
Name them: `answers_MODEL_NAME.txt` or `answers_MODEL_NAME.json`

### Step 4: Run the Evaluator
```
python 20_llm_baseline_evaluator.py
```

## Models to Test
- [ ] GPT-4.1 / GPT-4o (chat.openai.com)
- [ ] Claude Opus 4 / Claude Sonnet 4 (claude.ai)
- [ ] Gemini 2.5 Pro / Flash (gemini.google.com)
- [ ] DeepSeek Chat / Reasoner (chat.deepseek.com)
- [ ] Qwen3 (huggingface.co/chat or local)
- [ ] Llama 3.3 70B (meta.ai)
- [ ] Grok (x.com/grok)
- [ ] Mistral Large (chat.mistral.ai)
"""

    readme_path = os.path.join(OUTPUT_DIR, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme)
    print(f"  Created: {readme_path}")

    print(f"\nDone! All files in: {os.path.abspath(OUTPUT_DIR)}")


if __name__ == "__main__":
    main()
