from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    SUPABASE_URL: str
    SUPABASE_KEY: str
    QUICKNODE_SECURITY_TOKEN: str
    QUICKNODE_RPC_URL: str
    QUICKNODE_API_KEY: str
    MON_ADDRESS: str = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701".lower()
    MONAD_RPC_URL: str

    model_config = SettingsConfigDict(env_file=".env")

config = Config()