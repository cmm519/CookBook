#!/bin/sh
# Start Ollama and register the local distilled formatter GGUF when present.
set -eu

MODEL_NAME="${FORMATTER_MODEL:-cookbook-formatter}"
GGUF_PATH="${FORMATTER_GGUF_PATH:-/models/cookbook-formatter.gguf}"
MODELFILE="${FORMATTER_MODELFILE:-/models/Modelfile}"

ollama serve &
SERVE_PID=$!

for _ in $(seq 1 60); do
    if ollama list >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! ollama list >/dev/null 2>&1; then
    echo "ollama-bootstrap: Ollama API did not become ready" >&2
    kill "$SERVE_PID" 2>/dev/null || true
    exit 1
fi

if [ -f "$GGUF_PATH" ] && [ -f "$MODELFILE" ]; then
    if ! ollama show "$MODEL_NAME" >/dev/null 2>&1; then
        echo "ollama-bootstrap: registering $MODEL_NAME from $GGUF_PATH"
        ollama create "$MODEL_NAME" -f "$MODELFILE"
    else
        echo "ollama-bootstrap: $MODEL_NAME already registered"
    fi
else
    echo "ollama-bootstrap: GGUF or Modelfile missing — skip local model create" >&2
    echo "ollama-bootstrap: expected GGUF=$GGUF_PATH Modelfile=$MODELFILE" >&2
fi

wait "$SERVE_PID"
