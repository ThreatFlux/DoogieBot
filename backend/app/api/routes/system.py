from fastapi import APIRouter, Depends, HTTPException
from app.utils.deps import get_current_admin_user
from app.schemas.system import SystemSettings, SystemSettingsResponse
from app.services import system as system_service

router = APIRouter()

@router.get("", response_model=SystemSettingsResponse)
async def get_system_settings(
    current_user = Depends(get_current_admin_user)
):
    """
    Get current system settings.
    """
    settings = await system_service.get_system_settings()
    return {
        "settings": settings,
        "message": "System settings retrieved successfully"
    }

@router.put("", response_model=SystemSettingsResponse)
async def update_system_settings(
    settings_update: SystemSettings,
    current_user = Depends(get_current_admin_user)
):
    """
    Update system settings.
    """
    updated_settings = await system_service.update_system_settings(
        disable_sql_logs=settings_update.disable_sql_logs,
        log_level=settings_update.log_level
    )
    
    return {
        "settings": updated_settings,
        "message": "System settings updated successfully"
    }