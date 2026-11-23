# from pydantic_settings import BaseSettings, SettingsConfigDict


# class Settings(BaseSettings):
#     model_config = SettingsConfigDict(env_file=".env", extra="ignore")

#     azure_tenant_id: str
#     search_endpoint: str
#     search_index: str
#     mcp_api_client_id: str
#     sp_site_id: str
#     sp_results_list_id: str
#     sp_drafts_list_id: str
#     applicationinsights_connection_string: str = ""
#     portal_origin: str = "http://localhost:5173"
#     maintenance_mode: bool = False


# settings = Settings()


from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    azure_tenant_id: str
    search_endpoint: str
    search_index: str
    mcp_api_client_id: str
    sp_site_id: str
    sp_results_list_id: str
    sp_drafts_list_id: str
    applicationinsights_connection_string: str = ""
    portal_origin: str = "http://localhost:5173"
    allowed_hosts: str = "localhost:*,127.0.0.1:*"
    maintenance_mode: bool = False


settings = Settings()