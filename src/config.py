import os

def cfg():
    return {
        "PROJECT_ID": os.getenv("PROJECT_ID", ""),
        "APP_ID": os.getenv("GDR_APP_ID", ""),
        "DATA_STORE_ID": os.getenv("GDR_DATA_STORE_ID", ""),
        "LOCATION": os.getenv("GDR_LOCATION", "global"),
        "COLLECTION": os.getenv("GDR_COLLECTION", "default_collection"),
        "ASSISTANT": os.getenv("GDR_ASSISTANT", "default_assistant"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY", ""),
        # Academic search APIs
        "SEMANTIC_SCHOLAR_API_KEY": os.getenv("SEMANTIC_SCHOLAR_API_KEY", ""),
        "OPENALEX_EMAIL": os.getenv("OPENALEX_EMAIL", ""),
    }
