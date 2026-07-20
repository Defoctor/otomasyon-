# AŞAMA 3 local review panel

The FastAPI review panel binds only to `127.0.0.1`. It rejects any other
configured host. Background generation uses one worker by default, so
different episodes queue and FFmpeg renders do not run concurrently.

## Start

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\Activate.ps1
python run_panel.py
```

Open `http://127.0.0.1:8000`.

The panel supports demo generation, job progress and redacted errors, episode
history and preview, local approval/rejection, staging-based full or selected
scene regeneration, and confirmation-protected generated-media deletion.
Story, Character Bible, metadata, and the episode database row are preserved
by media deletion. This stage does not upload to YouTube.
