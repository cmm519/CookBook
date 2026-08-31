# cookbook-formatter (Q4_K_M)

Distilled recipe formatter GGUF for Ollama.

## Register locally

```bash
cd cursor1/models/cookbook-formatter
ollama create cookbook-formatter -f Modelfile
```

## Quick test

```bash
ollama run cookbook-formatter "transcript: brown ground beef with onion and garlic, add crushed tomatoes and simmer 30 min. caption: weeknight bolognese serves 4"
```

Or run the eval script (validates against CookBook `Recipe` schema):

```bash
cd cursor1
python scripts/test_formatter_model.py
```

## Use in CookBook

Set in `cursor1/.env`:

```env
FORMATTER_MODEL=cookbook-formatter
```

For Docker Compose, import the model into the **ollama** container (copy GGUF + Modelfile, then `ollama create` inside the container), or mount this folder and create there.

**Note:** `*.gguf` files are gitignored (~1.8 GB). Copy from the training output folder if missing.
