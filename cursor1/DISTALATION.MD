> **Status: ACTIVE (INC-10b)** — Distillation training lives in [`../cookbook model training/`](../cookbook%20model%20training/). CookBook still defaults to **`qwen2.5:7b-instruct`** until `cookbook-formatter` passes eval gates.

## Overview

Train a **Qwen2.5-3B** student (Unsloth LoRA, 4-bit) to replace the interim 7B Ollama formatter. Input is **full consolidated evidence** (transcript + caption/metadata + optional OCR). Output is **Pydantic-validated Recipe JSON** (not Markdown).

## Step 1: Generate the Distillation Dataset (Teacher)

1. Run CookBook download/transcribe/consolidate for Instagram/TikTok URLs.
2. Bootstrap to ~200 examples if needed (`bootstrap_corpus.py`).
3. Label with a flagship teacher (OpenAI/Ollama) or reference labels (`generate_teacher_labels.py`).
4. Export JSONL with fields: `instruction`, `input` (consolidated JSON), `output` (Recipe JSON).

Example JSONL row:

```json
{"instruction": "<SYSTEM_PROMPT>", "input": "{...consolidated...}", "output": "{...recipe...}"}
```
Use code with caution.Step 2: Set Up the Training Environment (The Student)You cannot easily train a model directly inside Ollama. You need a dedicated fine-tuning framework. The absolute easiest, most memory-efficient tool for consumer GPUs is Unsloth. It makes training 2x faster and uses 60% less VRAM.Install Unsloth and Dependencies: Create a Python environment on Linux (or Windows WSL2) and install the library:bashpip install "unsloth[colab-new] @ git+https://github.com"
pip install --no-deps trl peft transformers accelerate
Use code with caution.Select your Base Student Model: Choose Qwen/Qwen2.5-3B-Instruct or Qwen/Qwen2.5-1.5B-Instruct. They are already highly proficient at formatting tasks.Step 3: Run the Fine-Tuning Script (LoRA)Because you have an 8GB GPU, you will train using 4-bit LoRA quantization. This allows you to fine-tune a 3B model using only ~6GB of VRAM.Below is a Python blueprint script to execute your training.pythonimport os
from unsloth import FastLanguageModel
from datasets import load_dataset
from trl import SFTTrainer
from transformers import TrainingArguments

# 1. Configuration
max_seq_length = 4096 # Accommodate long video transcripts
model_name = "Qwen/Qwen2.5-3B-Instruct"

# 2. Load Model in 4-bit for 8GB VRAM safety
model, tokenizer = FastLanguageModel.from_pretrained(
    model_name = model_name,
    max_seq_length = max_seq_length,
    load_in_4bit = True,
)

# 3. Apply LoRA adapters (Only updates <1% of parameters)
model = FastLanguageModel.get_peft_model(
    model,
    r = 16, 
    target_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    lora_alpha = 16,
    lora_dropout = 0, 
    bias = "none",    
    use_gradient_checkpointing = "unsloth",
)

# 4. Load your generated distillation dataset
dataset = load_dataset("json", data_files="recipe_dataset.jsonl", split="train")

# 5. Setup Trainer
trainer = SFTTrainer(
    model = model,
    tokenizer = tokenizer,
    train_dataset = dataset,
    dataset_text_field = "text",
    max_seq_length = max_seq_length,
    dataset_num_proc = 2,
    packing = False, 
    args = TrainingArguments(
        per_device_train_batch_size = 2,
        gradient_accumulation_steps = 4,
        warmup_steps = 5,
        max_steps = 60, # Small dataset needs very few steps to learn format
        learning_rate = 2e-4,
        fp16 = True,
        logging_steps = 1,
        output_dir = "outputs",
    ),
)

# 6. Run Training
trainer_stats = trainer.train()

# 7. Save the model locally
model.save_pretrained_merged("custom-recipe-3b", tokenizer, save_method = "merged_16bit")
Use code with caution.Step 4: Quantize and Export Back to OllamaOnce your Python training finishes, you will have a folder containing your new, highly specialized model. To run it at maximum speed inside VS Code or your terminal via Ollama, you must convert it to a GGUF file.Convert to GGUF Format: Unsloth allows you to export directly to 4-bit GGUF with a single Python command right after training:pythonmodel.save_pretrained_gguf("custom-recipe-3b-q4", tokenizer, quantization_method = "q4_k_m")
Use code with caution.Move to Ollama: Move the resulting custom-recipe-3b-q4.gguf file into your local working directory.Create a Modelfile: Create a file named Modelfile and point it directly to your newly compiled weights:dockerfileFROM ./custom-recipe-3b-q4.gguf
SYSTEM "You are a specialized recipe extractor. Convert raw transcript text into structured Markdown recipes."
PARAMETER temperature 0.1
Use code with caution.Build and Run:bashollama create recipe-bot -f ./Modelfile
ollama run recipe-bot
Use code with caution.