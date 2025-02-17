from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ELASTICSEARCH_HOST: str = "elasticsearch"
    ELASTICSEARCH_PORT: int = 9200
    OPENAI_API_KEY: str = ""
    MAX_SEARCH_RESULTS: int = 10

    class Config:
        env_file = ".env"

settings = Settings()