from pydantic_settings import BaseSettings
import os

os.environ["CQLENG_ALLOW_SCHEMA_MANAGEMENT"] = "1"

class Settings(BaseSettings):
    database_hostname: str
    database_port: str
    database_name: str
    database_username: str
    database_password: str
    mqtt_hostname: str
    mqtt_port: str
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    
    astradb_keyspace: str
    astradb_client_id: str
    astradb_client_secret: str

    admin_password: str
    
    class Config:
        env_file = ".env"

settings = Settings()