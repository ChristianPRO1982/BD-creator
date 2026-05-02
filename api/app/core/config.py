from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="dev", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_log_level: str = Field(default="INFO", alias="APP_LOG_LEVEL")

    session_secret_key: str = Field(default="dev-session-secret", alias="SESSION_SECRET_KEY")
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")
    session_cookie_samesite: str = Field(default="lax", alias="SESSION_COOKIE_SAMESITE")

    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="bd_creator", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")

    auth_mode: str = Field(default="mock", alias="AUTH_MODE")
    auth_mock_base_url: str = Field(default="http://localhost:8001", alias="AUTH_MOCK_BASE_URL")
    auth_mock_shared_secret: str = Field(default="dev-shared-secret", alias="AUTH_MOCK_SHARED_SECRET")
    auth_mock_max_age_seconds: int = Field(default=300, alias="AUTH_MOCK_MAX_AGE_SECONDS")

    keycloak_server_url: str = Field(default="", alias="KEYCLOAK_SERVER_URL")
    keycloak_realm: str = Field(default="", alias="KEYCLOAK_REALM")
    keycloak_client_id: str = Field(default="", alias="KEYCLOAK_CLIENT_ID")
    keycloak_client_secret: str = Field(default="", alias="KEYCLOAK_CLIENT_SECRET")
    keycloak_redirect_uri: str = Field(default="", alias="KEYCLOAK_REDIRECT_URI")
    keycloak_logout_redirect_uri: str = Field(default="", alias="KEYCLOAK_LOGOUT_REDIRECT_URI")
    keycloak_scopes: str = Field(default="openid", alias="KEYCLOAK_SCOPES")

    user_schema: str = Field(default="users", alias="USER_SCHEMA")
    user_table: str = Field(default="users", alias="USER_TABLE")

    s3_endpoint_url: str = Field(default="http://minio:9000", alias="S3_ENDPOINT_URL")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")
    s3_bucket: str = Field(default="bd-assets", alias="S3_BUCKET")
    s3_use_ssl: bool = Field(default=False, alias="S3_USE_SSL")

    render_base_url: str = Field(default="http://web:5173", alias="RENDER_BASE_URL")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
