"""Start the local-only AŞAMA 3 review panel."""

import uvicorn

from app.core.config import Settings


def main() -> None:
    settings = Settings.from_env()
    if settings.web_host != "127.0.0.1":
        raise RuntimeError(
            "Unsafe WEB_HOST rejected. The panel only supports 127.0.0.1."
        )
    uvicorn.run(
        "app.web.app:create_web_app",
        factory=True,
        host=settings.web_host,
        port=settings.web_port,
        reload=False,
        workers=1,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
