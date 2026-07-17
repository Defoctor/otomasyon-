from src.pipeline import load_topics, run_pipeline


if __name__ == "__main__":
    result = run_pipeline(load_topics()[0], target_minutes=5)
    print(f"Proje: {result['project_dir']}")
    print(result["message"])

