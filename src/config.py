from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "extra": "ignore"}

    # Database
    database_url: str = "postgresql+asyncpg://jeans:jeans_dev_2024@localhost:5432/jeans_ai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = ""
    aws_region: str = "us-east-1"

    # AI Services
    replicate_api_token: str = ""
    kling_api_key: str = ""
    runway_api_key: str = ""

    # Paths
    assets_dir: str = "assets"
    output_dir: str = "output"


settings = Settings()
