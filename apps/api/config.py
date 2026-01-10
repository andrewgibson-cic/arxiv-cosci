"""
API Configuration
Loads environment variables and provides configuration settings.
"""
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """API configuration settings."""
    
    # API Settings
    api_title: str = "ArXiv Co-Scientist API"
    api_version: str = "0.4.0"
    debug: bool = False
    
    # Neo4j Settings
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    neo4j_password: str = Field(default="password", alias="NEO4J_PASSWORD")
    
    # ChromaDB Settings
    chroma_persist_dir: str = Field(default="./data/chroma", alias="CHROMA_PERSIST_DIR")
    
    # LLM Settings
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    gemini_api_key: Optional[str] = Field(default=None, alias="GEMINI_API_KEY")
    groq_api_key: Optional[str] = Field(default=None, alias="GROQ_API_KEY")
    
    # Semantic Scholar API
    s2_api_key: Optional[str] = Field(default=None, alias="S2_API_KEY")
    
    # Pagination
    default_page_size: int = 20
    max_page_size: int = 100
    
    # Search Settings
    default_search_limit: int = 10
    max_search_limit: int = 50
    
    # Graph Settings
    default_graph_depth: int = 2
    max_graph_depth: int = 5
    max_graph_nodes: int = 1000
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()