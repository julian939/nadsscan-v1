from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    QUICKNODE_SECURITY_TOKEN: str
    QUICKNODE_RPC_URL: str
    QUICKNODE_API_KEY: str
    DATABASE_URL: str  # HINZUGEFÜGT
    MON_ADDRESS: str = "0x760AfE86e5de5fa0Ee542fc7B7B713e1c5425701"
    MONAD_RPC_URL: str

    model_config = SettingsConfigDict(env_file=".env")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Normalize MON address on initialization
        self.MON_ADDRESS = self.MON_ADDRESS.lower()


config = Config()