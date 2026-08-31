# CookBook

Local-first recipe repository from Instagram Reels.

**All application code, Docker config, and docs live in [`cursor1/`](cursor1/).**

## Quick start

```bash
cd cursor1
# First time: double-click CookBook-Setup.bat
# Or manually:
cp .env.example .env   # if needed
docker compose up -d --build
```

Then open [http://localhost:8080](http://localhost:8080).

| Start here | Path |
|---|---|
| User guide | [`cursor1/USER_GUIDE.md`](cursor1/USER_GUIDE.md) |
| Software requirements | [`cursor1/SOFTWARE_REQUIREMENTS.md`](cursor1/SOFTWARE_REQUIREMENTS.md) |
| Docker | [`cursor1/DOCKER.md`](cursor1/DOCKER.md) |
| Demo seed | `cd cursor1 && python scripts/seed_demo_recipes.py` |
