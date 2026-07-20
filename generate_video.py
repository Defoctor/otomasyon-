from src.pipeline import load_topics, run_pipeline


def main():
    result = run_pipeline(load_topics()[0], target_minutes=5)
    generated = sum(
        item.status == "generated" for item in result["animation_results"]
    )
    print(f"Animasyon klipleri: {generated}")
    print(f"Proje: {result['project_dir']}")


if __name__ == "__main__":
    main()
