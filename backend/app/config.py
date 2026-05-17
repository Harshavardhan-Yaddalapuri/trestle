from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_service_key: str

    # IBM WatsonX (optional for now)
    watsonx_api_key: str | None = None
    watsonx_project_id: str | None = None
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"

    # Tavily search
    tavily_api_key: str | None = None

    # Firecrawl scraping
    firecrawl_api_key: str | None = None

    # OpenAI fallback
    openai_api_key: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
