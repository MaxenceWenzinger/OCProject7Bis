from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    database_url: str = "postgresql+psycopg://user:password@localhost:5432/dbname"
    anthropic_api_key: str | None = None
    llm_model: str = "claude-haiku-5-5"
    judge_model: str = "claude-haiku-5-5"
    # When set, POST /rebuild requires the header "X-Admin-Token: <admin_token>"
    admin_token: str | None = None

settings = Settings()
