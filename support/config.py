import os


def env(name: str, default: str) -> str:
    return os.environ.get(f"SUPPORT_{name}", default)


OLLAMA_URL = env("OLLAMA_URL", "http://localhost:11434")
MODEL = env("MODEL", "qwen3:4b-instruct")
EMBED_MODEL = env("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
DOCS_DIR = env("DOCS_DIR", "help_docs")
INDEX_DIR = env("INDEX_DIR", ".chroma")
DB = env("DB", "support.db")
# Start narrow: in FAQ-only mode account questions escalate instead of using tools.
FAQ_ONLY = env("FAQ_ONLY", "1") == "1"
