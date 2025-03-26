from pydantic import BaseModel
from typing import Optional, Literal

class SystemSettings(BaseModel):
    disable_sql_logs: Optional[bool] = None
    log_level: Optional[Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]] = None

class SystemSettingsResponse(BaseModel):
    settings: SystemSettings
    message: str