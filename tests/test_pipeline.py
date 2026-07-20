import base64
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from src import pipeline
from src.character_design import CharacterDesignStore
from src.memory import MEMORY_DEFAULTS, MemoryStore
from src.providers.content import OpenAIContentProvider
from src.providers.media import FakeMediaProvider, OpenAIImageProvider
from src.providers.voice import ElevenLabsMultiVoiceProvider, ElevenLabsVoiceProvider


def test_pipeline_creates_safe_package(monkeypatch):
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        monkeypatch.setattr(pipeline.settings, "projects_dir", Path(temp_dir))
        monkeypatch.setattr(pipeline.settings, "memory_dir", Path(temp_dir) / "memory")
        monkeypatch.setattr(
            pipeline.settings,
            "character_designs_dir",
            Path(temp_dir) / "character-designs",
        )
        monkeypatch.setattr(pipeline.settings, "content_provider", "fake")
        monkeypatch.setattr(pipeline.settings, "media_provider", "fake")
        monkeypatch.setattr(pipeline.settings, "voice_provider", "fake")
        monkeypatch.setattr(pipeline.settings, "video_provider", "none")
        monkeypatch.setattr(pipeline, "build_video", lambda folder, count: (None, "test"))
        topic = pipeline.load_topics()[0]
        result = pipeline.run_pipeline(topic, 5)
        project = result["project_dir"]
        assert (project / "metadata.json").exists()
        assert (project / "thumbnail.png").exists()
        images = list((project / "images").glob("*.png"))
        assert len(images) == len(result["content"].scenes)
        assert len(images) > 8
        assert all(
            5 <= scene.duration_seconds <= 8
            for scene in result["content"].scenes
        )
        assert result["scene_manifest"].exists()
        assert result["image_failures"] == 0
        assert result["shorts_path"] is None
        assert result["narration_path"] is None
        assert result["youtube_package"].exists()
        youtube_ready = json.loads(
            result["youtube_package"].read_text(encoding="utf-8")
        )
        assert youtube_ready["requires_human_approval"] is True
        assert youtube_ready["made_for_kids"] is True
        assert youtube_ready["privacy_status"] == "private"
        approval = json.loads(
            (project / "approval_status.json").read_text(encoding="utf-8")
        )
        assert approval["approved"] is False
        assert approval["youtube_uploaded"] is False


def test_content_provider_selection(monkeypatch):
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        monkeypatch.setattr(pipeline.settings, "memory_dir", Path(temp_dir))
        monkeypatch.setattr(pipeline.settings, "content_provider", "fake")
        assert isinstance(pipeline.get_content_provider(), pipeline.FakeContentProvider)

        monkeypatch.setattr(pipeline.settings, "content_provider", "openai")
        monkeypatch.setattr(pipeline.settings, "openai_model", "test-model")
        provider = pipeline.get_content_provider()
        assert isinstance(provider, pipeline.OpenAIContentProvider)
        assert provider.model == "test-model"


def test_unknown_content_provider_fails(monkeypatch):
    monkeypatch.setattr(pipeline.settings, "content_provider", "unknown")
    try:
        pipeline.get_content_provider()
    except ValueError as exc:
        assert "Desteklenmeyen CONTENT_PROVIDER" in str(exc)
    else:
        raise AssertionError("Bilinmeyen sağlayıcı reddedilmeliydi.")


def test_openai_provider_uses_responses_api():
    scenes = [
        {"narration": f"Scene {number} tells a gentle part of the story.",
         "visual_prompt": f"Child-friendly illustration for scene {number}."}
        for number in range(1, 9)
    ]
    response = SimpleNamespace(
        output_text=json.dumps(
            {
                "title": "A Small Brave Star",
                "description": "A warm story about kindness.",
                "tags": ["children", "kindness", "bedtime"],
                "scenes": scenes,
                "memory": {
                    **MEMORY_DEFAULTS,
                    "characters": {
                        "characters": [
                            {
                                "name": "Mira",
                                "appearance": "curly brown hair",
                                "personality": "kind and curious",
                            }
                        ]
                    },
                    "timeline": {
                        "events": [
                            {
                                "title": "A Small Brave Star",
                                "summary": "Mira helped a lost star.",
                            }
                        ]
                    },
                },
            }
        )
    )

    class FakeResponses:
        def __init__(self):
            self.call = None

        def create(self, **kwargs):
            self.call = kwargs
            return response

    fake_responses = FakeResponses()
    fake_client = SimpleNamespace(responses=fake_responses)
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        memory_store = MemoryStore(Path(temp_dir))
        memory_store.update(
            {
                "world": {
                    "facts": ["Stars can speak softly in this story world."]
                }
            }
        )
        provider = OpenAIContentProvider(
            model="test-model",
            memory_store=memory_store,
            client=fake_client,
        )

        content = provider.generate(
            {"title": "Stars", "angle": "Helping friends", "audience": "children"},
            5,
        )

        assert fake_responses.call["model"] == "test-model"
        assert "5 minutes" in fake_responses.call["input"]
        assert "Stars can speak softly" in fake_responses.call["input"]
        assert content.title == "A Small Brave Star"
        assert len(content.scenes) == 8
        assert content.script.startswith("Scene 1")
        saved = memory_store.load_all()
        assert saved["characters"]["characters"][0]["name"] == "Mira"
        assert saved["timeline"]["events"][0]["title"] == "A Small Brave Star"


def test_memory_merge_preserves_character_details():
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        store = MemoryStore(Path(temp_dir))
        store.update(
            {
                "characters": {
                    "characters": [
                        {
                            "name": "Mira",
                            "appearance": "curly brown hair",
                            "personality": "kind",
                        }
                    ]
                }
            }
        )
        store.update(
            {
                "characters": {
                    "characters": [
                        {"name": "Mira", "personality": "kind and brave"}
                    ]
                }
            }
        )

        character = store.load_all()["characters"]["characters"][0]
        assert character["appearance"] == "curly brown hair"
        assert character["personality"] == "kind and brave"


def test_character_design_prompt_and_memory_sync():
    source = Path("assets/characters/leo.json")
    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        directory = Path(temp_dir)
        shutil.copy(source, directory / "leo.json")
        store = CharacterDesignStore(directory)

        prompt = store.build_scene_prompt(
            "Leo explores a forest path.", "Leo smiles and checks the map."
        )
        assert "Character design references:" in prompt
        assert "blue hoodie" in prompt
        assert "Negative prompt:" in prompt
        assert "watermark" in prompt

        store.sync_from_memory(
            {
                "characters": {
                    "characters": [
                        {
                            "id": "leo",
                            "name": "Leo",
                            "age": 11,
                            "species": "human",
                            "appearance": {
                                "hair": "brown",
                                "eyes": "green",
                                "signature_clothing": "red hoodie",
                            },
                            "personality": ["brave", "curious"],
                        }
                    ]
                }
            }
        )
        updated = store.load_all()["leo"]
        assert updated["age"] == 11
        assert updated["clothes"] == "red hoodie"
        assert "red hoodie" in updated["prompt"]
        assert updated["memory_snapshot"]["age"] == 11


def test_openai_image_provider_uses_images_api():
    png_bytes = b"\x89PNG\r\n\x1a\nfake-image"
    image_result = SimpleNamespace(
        data=[
            SimpleNamespace(
                b64_json=base64.b64encode(png_bytes).decode("ascii")
            )
        ]
    )

    class FakeImages:
        def __init__(self):
            self.call = None

        def generate(self, **kwargs):
            self.call = kwargs
            return image_result

    fake_images = FakeImages()
    client = SimpleNamespace(images=fake_images)
    provider = OpenAIImageProvider(
        model="gpt-image-test",
        size="1536x1024",
        quality="medium",
        client=client,
    )

    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        output = Path(temp_dir) / "images" / "scene_01.png"
        provider.create_scene("Leo and Scout in the forest", output, "SCENE 1")

        assert output.read_bytes() == png_bytes
        assert fake_images.call == {
            "model": "gpt-image-test",
            "prompt": "Leo and Scout in the forest",
            "size": "1536x1024",
            "quality": "medium",
        }


def test_image_failure_is_logged_and_uses_fallback():
    class FailingProvider:
        def create_scene(self, prompt, output_path, label):
            raise RuntimeError("temporary image service failure")

    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        root = Path(temp_dir)
        output = root / "images" / "scene_01.png"
        error_log = root / "image_generation_errors.jsonl"

        success = pipeline.create_scene_image_safely(
            FailingProvider(),
            FakeMediaProvider(),
            "Leo in his blue hoodie",
            output,
            "SCENE 1",
            error_log,
        )

        assert success is False
        assert output.exists()
        error = json.loads(error_log.read_text(encoding="utf-8"))
        assert error["error_type"] == "RuntimeError"
        assert error["scene"] == "SCENE 1"


def test_elevenlabs_provider_creates_story_mp3():
    class FakeTextToSpeech:
        def __init__(self):
            self.call = None

        def convert(self, **kwargs):
            self.call = kwargs
            return iter([b"ID3", b"test-mp3-audio"])

    text_to_speech = FakeTextToSpeech()
    client = SimpleNamespace(text_to_speech=text_to_speech)
    provider = ElevenLabsVoiceProvider(
        voice_id="test-voice",
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
        client=client,
    )

    with TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        output = Path(temp_dir) / "narration.mp3"
        provider.synthesize_story("Leo and Scout begin an adventure.", output)

        assert output.read_bytes() == b"ID3test-mp3-audio"
        assert text_to_speech.call == {
            "voice_id": "test-voice",
            "model_id": "eleven_multilingual_v2",
            "output_format": "mp3_44100_128",
            "text": "Leo and Scout begin an adventure.",
        }


def test_voice_provider_selection(monkeypatch):
    monkeypatch.setattr(pipeline.settings, "voice_provider", "elevenlabs")
    monkeypatch.setattr(pipeline.settings, "elevenlabs_voice_id", "test-voice")
    provider = pipeline.get_voice_provider()
    assert isinstance(provider, ElevenLabsVoiceProvider)
    assert provider.voice_id == "test-voice"

    monkeypatch.setattr(pipeline.settings, "voice_provider", "elevenlabs_multi")
    monkeypatch.setattr(
        pipeline.settings,
        "elevenlabs_voice_ids",
        {
            "narrator": "narrator-id",
            "leo": "leo-id",
            "scout": "scout-id",
            "mother": "mother-id",
            "father": "father-id",
        },
    )
    multi_provider = pipeline.get_voice_provider()
    assert isinstance(multi_provider, ElevenLabsMultiVoiceProvider)
    assert multi_provider.voice_ids["scout"] == "scout-id"
