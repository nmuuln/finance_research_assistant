import os
from dotenv import load_dotenv
from src.pipeline import run_pipeline

def main():
    load_dotenv()
    topic = os.getenv("TOPIC") or "Sovereign spread dynamics during rate-hiking cycles"
    language = os.getenv("LANGUAGE", "mn")
    out = run_pipeline(topic, include_web=True, language=language)
    print("\n=== PIPELINE RESULT ===")
    for k, v in out.items():
        if k.endswith("_preview"):
            print(f"{k}: {v[:400]}{'...' if len(v) > 400 else ''}")
        else:
            print(f"{k}: {v}")

if __name__ == "__main__":
    main()
