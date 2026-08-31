#!/bin/sh
set -eu

MODE="${MODE:-test}"

ensure_dirs() {
    mkdir -p \
        /data/recipes \
        /data/working \
        /data/db \
        /data/dataset/raw \
        /data/dataset/transcripts
}

validate_tools() {
    command -v ffmpeg >/dev/null 2>&1 || { echo "ffmpeg not found" >&2; exit 1; }
    command -v yt-dlp >/dev/null 2>&1 || python -c "import yt_dlp" 2>/dev/null || {
        echo "yt-dlp not found" >&2
        exit 1
    }
}

ensure_dirs
validate_tools

case "${MODE}" in
    download)
        exec python -m app.cli download "$@"
        ;;
    transcribe)
        exec python -m app.cli transcribe "$@"
        ;;
    import)
        exec python -m app.cli import "$@"
        ;;
    web)
        exec python -c "from app.web.run import run_production; run_production()"
        ;;
    testing-gui)
        exec python -c "from app.web.run import run_testing_gui; run_testing_gui()"
        ;;
    deployment-gui)
        exec python -c "from app.web.run import run_deployment_gui; run_deployment_gui()"
        ;;
    test)
        exec pytest "$@"
        ;;
    *)
        echo "Unknown MODE=${MODE}. Valid: download, transcribe, import, web, testing-gui, deployment-gui, test" >&2
        exit 1
        ;;
esac
