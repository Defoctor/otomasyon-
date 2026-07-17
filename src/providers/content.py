from abc import ABC, abstractmethod

from src.models import ContentPackage, Scene


class ContentProvider(ABC):
    @abstractmethod
    def generate(self, topic: dict, target_minutes: int) -> ContentPackage:
        raise NotImplementedError


class FakeContentProvider(ContentProvider):
    """API anahtarı kullanmadan deterministik test içeriği üretir."""

    def generate(self, topic: dict, target_minutes: int) -> ContentPackage:
        title = f"{topic['title']}: Bildiğimizi Sandığımız 5 Gerçek"
        intro = (
            f"Bugün {topic['title'].lower()} konusuna bakıyoruz. "
            "Efsanelerle doğrulanabilir bilgileri ayırıp en ilginç ayrıntıları inceleyeceğiz."
        )
        facts = [
            "İlk ipucu, eski haritalar ile modern araştırmaların aynı noktada buluşmasıdır.",
            "İkinci ayrıntı, dönemin insanlarının sanılandan daha gelişmiş yöntemler kullanmasıdır.",
            "Üçüncü bulgu, popüler anlatıların her zaman arkeolojik kanıtlarla uyuşmadığını gösterir.",
            "Dördüncü nokta, coğrafyanın insanların kararlarını nasıl değiştirdiğini açıklar.",
            "Son ayrıntı ise yeni araştırmaların eski kabulleri hâlâ değiştirebildiğini hatırlatır.",
        ]
        outro = (
            "Bu hikâyenin en güçlü tarafı, kesin cevaplardan çok yeni sorular doğurması. "
            "Benzer kısa belgeseller için kanalı takip edebilirsiniz."
        )
        paragraphs = [intro] + facts + [outro]
        # Demo kısa tutulur; gerçek sağlayıcı hedef süreye göre metni genişletir.
        scene_duration = max(5, round(target_minutes * 60 / len(paragraphs)))
        scenes = [
            Scene(
                number=index,
                narration=text,
                visual_prompt=f"Belgesel tarzı, sinematik, telifsiz özgün sahne: {text}",
                duration_seconds=scene_duration,
            )
            for index, text in enumerate(paragraphs, start=1)
        ]
        return ContentPackage(
            topic=topic["title"],
            title=title,
            description=(
                f"{topic['title']} hakkında kaynak kontrolüne uygun, kısa belgesel anlatımı.\n\n"
                "Not: Bu sürüm test verisi üretir; yayınlamadan önce bilgi ve kaynak kontrolü yapın."
            ),
            tags=["tarih", "belgesel", "ilginç bilgiler", "gizem", "kısa belgesel"],
            script="\n\n".join(paragraphs),
            scenes=scenes,
        )

