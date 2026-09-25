# CookBook — Project Description

CookBook is a local-first recipe repository. A person pastes an Instagram Reel URL. The system downloads the video, transcribes the audio, optionally reads on-screen text, and turns that evidence into a structured recipe that can be searched, edited, rated, and turned into a grocery list.

It runs on a personal server with Docker. Speech-to-text and recipe formatting stay on that machine. Recipe files on disk are the source of truth. A SQLite index supports search.

## Problem

Cooking videos on Instagram often split a recipe across spoken steps, on-screen text, the caption, and comments. Re-watching the reel is the only way to recover quantities and order. CookBook keeps the original video and the raw evidence, then produces a cookbook-style recipe from them.

## Users

| Audience | What they do |
|---|---|
| End user | Import reels, browse and edit recipes, rate them, build a shopping list, file a bug report |
| Deployer | Install the Docker stack, choose storage paths, manage models and health |
| Tester | Run each pipeline step alone and inspect intermediate files |

End users use the production web app. They do not install Docker or edit configuration.

## What a successful import produces

One folder per recipe, containing:

- the original video
- the raw transcript (plain text and timestamped segments)
- optional vision/OCR evidence
- validated recipe JSON
- a Markdown rendering of that JSON
- import metadata
- a matching row in the search index

## Pipeline

1. Download the video and metadata (yt-dlp).
2. Extract audio (ffmpeg, mono 16 kHz WAV).
3. Transcribe with faster-whisper.
4. Extract frames (optional).
5. Read on-screen text with OCR (optional).
6. Consolidate transcript, vision, metadata, and any user note or custom instruction.
7. Format a structured recipe with a local Ollama model.
8. Validate the JSON and render Markdown without a language model.
9. Store the package and update the SQLite index.

The formatter must not invent quantities. Unknown amounts stay empty and may carry a confidence score. Raw transcripts are never overwritten by the formatter.

## How it runs

Two containers: the application and an Ollama sidecar for the formatter. The host needs Docker Engine and Docker Compose. A GPU host also needs an NVIDIA driver and the NVIDIA Container Toolkit. Whisper and the formatter share the GPU one at a time so an 8 GB card can run both.

Three web interfaces, started by a `MODE` setting:

| Interface | Port | Who uses it |
|---|---|---|
| Production | 8080 | End user |
| Testing | 8081 | Tester |
| Deployment | 8082 | Deployer |

The default formatter model is `cookbook-formatter`, loaded from a local GGUF file. `qwen2.5:7b-instruct` is the fallback when that file is not installed.

A separate dataset path supports batch download and transcription of reels before they are imported as recipes.

## Out of scope

Cloud hosting, user accounts, and publishing back to Instagram. A scheduled agent that triages bug reports is specified for later and is not part of the current product. The application language is Python. A Java service is not part of this system.
