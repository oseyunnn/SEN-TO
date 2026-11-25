import pytest

from ai.generation import OllamaChatProvider, OpenAIResponsesProvider
from ai.rag_factory import ChromaRetriever, build_default_pipeline


def test_default_pipeline_uses_local_ollama_and_lazy_chroma(monkeypatch, tmp_path):
    monkeypatch.delenv("SENTO_GENERATOR_PROVIDER", raising=False)
    monkeypatch.setenv("SENTO_CHROMA_PATH", str(tmp_path / "not-created-yet"))

    pipeline = build_default_pipeline()

    assert isinstance(pipeline.generator.provider, OllamaChatProvider)
    assert isinstance(pipeline.retriever, ChromaRetriever)
    assert not pipeline.retriever.persist_directory.exists()


def test_openai_generator_can_be_selected_without_startup_api_call(monkeypatch, tmp_path):
    monkeypatch.setenv("SENTO_GENERATOR_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://aiki-labs.up.railway.app/api/v1")
    monkeypatch.setenv("SENTO_CHROMA_PATH", str(tmp_path / "local-index"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    pipeline = build_default_pipeline()

    assert isinstance(pipeline.generator.provider, OpenAIResponsesProvider)
    assert pipeline.generator.provider.model == "gpt-6-luna"
    assert pipeline.generator.provider.base_url == "https://aiki-labs.up.railway.app/api/v1"
    assert pipeline.retriever.persist_directory == tmp_path / "local-index"


def test_unknown_generator_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("SENTO_GENERATOR_PROVIDER", "unknown")
    with pytest.raises(ValueError, match="must be 'ollama' or 'openai'"):
        build_default_pipeline()
