import logging
from app.core.config import settings

# Get the SQLAlchemy logger
sqlalchemy_logger = logging.getLogger('sqlalchemy.engine')
# Get the root logger
root_logger = logging.getLogger()

# Map string log levels to logging constants
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

async def get_system_settings():
    """Get current system settings"""
    # Get current log level name
    current_level = logging.getLevelName(root_logger.level)
    
    return {
        "disable_sql_logs": settings.DISABLE_SQL_LOGS,
        "log_level": current_level
    }

async def update_system_settings(disable_sql_logs=None, log_level=None):
    """Update system settings"""
    if disable_sql_logs is not None:
        # Update the setting in memory
        settings.DISABLE_SQL_LOGS = disable_sql_logs
        # Update the SQLAlchemy logger level
        if disable_sql_logs:
            # Set to WARNING level to completely hide the SQL queries
            sqlalchemy_logger.setLevel(logging.WARNING)
        else:
            sqlalchemy_logger.setLevel(logging.DEBUG)
            sqlalchemy_logger.setLevel(logging.DEBUG)
    
    if log_level is not None and log_level in LOG_LEVELS:
        # Update the root logger level
        root_logger.setLevel(LOG_LEVELS[log_level])
        
        # Update all loggers except SQLAlchemy if SQL logs are disabled
        for logger_name in logging.root.manager.loggerDict:
            logger = logging.getLogger(logger_name)
            
            # SQLAlchemy loggers are handled separately based on the disable_sql_logs setting
            if logger_name.startswith('sqlalchemy'):
                # Don't change SQLAlchemy logger levels here - they're controlled by the disable_sql_logs setting
                continue
                
            # Set the log level for all other loggers
            logger.setLevel(LOG_LEVELS[log_level])
        
    return await get_system_settings()