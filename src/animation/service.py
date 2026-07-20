import os
from typing import Any, Callable

from .models import AnimationSubmission, SceneAnimation


class HiggsfieldConfigurationError(RuntimeError):
    pass


HiggsfieldTransport = Callable[
    [str, str, dict[str, Any]],
    dict[str, Any],
]


class HiggsfieldAnimationService:
    """Higgsfield API sözleşmesini pipeline'dan izole eden servis katmanı."""

    def __init__(
        self,
        api_key: str | None = None,
        endpoint: str | None = None,
        transport: HiggsfieldTransport | None = None,
    ):
        self.api_key = api_key or os.getenv("HIGGSFIELD_API_KEY", "")
        self.endpoint = endpoint or os.getenv("HIGGSFIELD_API_URL", "")
        self.transport = transport

    def submit_scene(self, scene: SceneAnimation) -> AnimationSubmission:
        if not self.api_key:
            raise HiggsfieldConfigurationError(
                "HIGGSFIELD_API_KEY tanımlanmadan animasyon gönderilemez."
            )
        if not self.endpoint:
            raise HiggsfieldConfigurationError(
                "HIGGSFIELD_API_URL tanımlanmadan animasyon gönderilemez."
            )
        if self.transport is None:
            raise HiggsfieldConfigurationError(
                "Resmî Higgsfield API taşıyıcısı yapılandırılmadı; "
                "henüz ağ isteği yapılmadı."
            )

        response = self.transport(self.endpoint, self.api_key, scene.to_payload())
        submission_id = response.get("id") or response.get("submission_id")
        if not submission_id:
            raise RuntimeError("Higgsfield yanıtında gönderim kimliği bulunamadı.")
        return AnimationSubmission(
            submission_id=str(submission_id),
            status=str(response.get("status", "submitted")),
            raw_response=response,
        )


def submit_to_higgsfield(
    scene: SceneAnimation,
    service: HiggsfieldAnimationService | None = None,
) -> AnimationSubmission:
    """Bir sahneyi Higgsfield servis katmanına gönderen tek giriş noktası."""

    return (service or HiggsfieldAnimationService()).submit_scene(scene)
