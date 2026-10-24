"""Application settings, loaded from environment / .env."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Google Lens (vision) -------------------------------------------
    # auto | serpapi | gcp_vision | google_lens | mock
    lens_provider: str = "auto"
    serpapi_key: str = ""                       # serpapi.com Google Lens API
    gcp_vision_api_key: str = ""                # Cloud Vision (WEB_DETECTION)
    lens_country: str = "in"                    # market for Lens results
    lens_hl: str = "en"                         # language hint for Lens

    # --- Sarvam AI (multilingual) ---------------------------------------
    sarvam_api_key: str = ""

    # --- Marketplace enrichment (optional) ------------------------------
    enable_marketplace_search: bool = True
    amazon_access_key: str = ""
    amazon_secret_key: str = ""
    amazon_partner_tag: str = ""

    # --- Runtime --------------------------------------------------------
    request_timeout: float = 40.0
    max_upload_mb: float = 12.0
    max_results: int = 6


settings = Settings()
