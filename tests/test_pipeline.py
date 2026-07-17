import json

from src import pipeline


def test_pipeline_creates_safe_package(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline.settings, "projects_dir", tmp_path)
    monkeypatch.setattr(pipeline, "build_video", lambda folder, count: (None, "test"))
    topic = pipeline.load_topics()[0]
    result = pipeline.run_pipeline(topic, 5)
    project = result["project_dir"]
    assert (project / "metadata.json").exists()
    assert (project / "thumbnail.png").exists()
    assert len(list((project / "scenes").glob("*.png"))) == 7
    approval = json.loads((project / "approval_status.json").read_text(encoding="utf-8"))
    assert approval["approved"] is False
    assert approval["youtube_uploaded"] is False

