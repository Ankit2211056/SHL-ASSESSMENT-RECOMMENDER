from main import resolve_api_key


def test_resolve_api_key_reads_dotenv_from_project_root(tmp_path, monkeypatch):
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text('GEMINI_API_KEY="test-key-from-dotenv"\n', encoding="utf-8")

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_GENAI_API_KEY", raising=False)

    assert resolve_api_key(base_dir=tmp_path) == "test-key-from-dotenv"
