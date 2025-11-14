"""Configuration classes using Pydantic BaseSettings."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class PromptConfig(BaseSettings):
    """Prompt configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FIREWALL_PROMPT_", case_sensitive=False
    )

    max_prompt_chars: int = 4000
    block_on_match: bool = True
    log_samples: bool = True


class VectorizerConfig(BaseSettings):
    """Vectorizer configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FIREWALL_VECTORIZER_", case_sensitive=False
    )

    model: str = "sentence-transformers/all-MiniLM-L6-v2"


class QdrantConfig(BaseSettings):
    """Qdrant vector store configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FIREWALL_QDRANT_", case_sensitive=False
    )

    url: str = "http://localhost:6333"
    collection_name: str = "firewall_vectors"
    enabled: bool = False


class MLConfig(BaseSettings):
    """Machine Learning models configuration."""

    model_config = SettingsConfigDict(env_prefix="FIREWALL_ML_", case_sensitive=False)

    pii_model: Optional[str] = None
    toxicity_model: Optional[str] = "models/toxicity_model.onnx"
    toxicity_tokenizer: str = "unitary/toxic-bert"
    prompt_injection_model: str = "ProtectAI/deberta-v3-base-prompt-injection-v2"


class HeuristicConfig(BaseSettings):
    """Heuristic detector configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FIREWALL_HEURISTIC_", case_sensitive=False
    )

    rules_path: str = "rules/prompt_injection_rules.yaml"


class PolicyConfig(BaseSettings):
    """Policy engine configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FIREWALL_POLICY_", case_sensitive=False
    )

    policies_path: str = "policy_engine/policies.rego"
    opa_url: str = "http://localhost:8181"
    opa_policy_name: str = "firewall/policy"


class LoggingConfig(BaseSettings):
    """Logging configuration."""

    model_config = SettingsConfigDict(
        env_prefix="FIREWALL_LOGGING_", case_sensitive=False
    )

    type: str = "print"


class FirewallConfig(BaseSettings):
    """Main firewall configuration."""

    model_config = SettingsConfigDict(
        env_prefix="",
    )

    prompt: PromptConfig = PromptConfig()
    vectorizer: VectorizerConfig = VectorizerConfig()
    qdrant: QdrantConfig = QdrantConfig()
    ml: MLConfig = MLConfig()
    heuristic: HeuristicConfig = HeuristicConfig()
    policy: PolicyConfig = PolicyConfig()
    logging: LoggingConfig = LoggingConfig()


# Create a single config instance to be used across the application
config = FirewallConfig()
