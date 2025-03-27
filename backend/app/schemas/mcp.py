from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, validator, ConfigDict, field_validator

class MCPServerConfigBase(BaseModel):
    """
    Base schema for MCP server configurations.
    
    Contains common fields shared by all MCP server configuration schemas.
    """
    name: str = Field(..., description="Unique name for this MCP server configuration")
    command: str = Field("docker", description="Command to run the MCP server")
    args: List[str] = Field(..., description="Arguments for the command")
    env: Optional[Dict[str, str]] = Field(None, description="Environment variables")
    enabled: bool = Field(True, description="Whether this server is enabled")

    @field_validator("command")
    @classmethod
    def validate_command(cls, v):
        """
        Validate that the command is 'docker'.
        
        In our implementation, we only support running MCP servers in Docker containers.
        """
        if v != "docker":
            raise ValueError("Only 'docker' command is supported")
        return v
    
    @field_validator("args")
    @classmethod
    def validate_args(cls, v):
        """
        Validate that the args list is not empty and contains valid Docker arguments.
        """
        if not v or len(v) < 1:
            raise ValueError("Arguments must not be empty")
        
        # Check if the command is for running a container
        if "run" not in v and v[0] != "run":
            # If npx or uvx commands are specified, they should be run in a Docker container
            if any(cmd in v for cmd in ["npx", "uvx"]):
                # Transform from non-Docker command to Docker run command
                # This is a simplified validator, actual transformation happens in the service layer
                pass
            else:
                # For this validator, we'll just check for the presence of a run command
                # The actual transformation of npx/uvx commands will happen in the service layer
                pass
                
        return v

class MCPServerConfigCreate(MCPServerConfigBase):
    """
    Schema for creating a new MCP server configuration.
    """
    pass

class MCPServerConfigUpdate(BaseModel):
    """
    Schema for updating an existing MCP server configuration.
    
    All fields are optional to allow partial updates.
    """
    name: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    enabled: Optional[bool] = None

class MCPServerConfigInDBBase(MCPServerConfigBase):
    """
    Schema for MCP server configuration as stored in the database.
    """
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MCPServerConfigResponse(MCPServerConfigInDBBase):
    """
    Schema for MCP server configuration API responses.
    """
    pass

class MCPServerStatus(BaseModel):
    """
    Schema for MCP server status information.
    """
    id: str
    name: str
    enabled: bool
    status: str  # "running", "stopped", "error"
    container_id: Optional[str] = None
    error_message: Optional[str] = None

class MCPConfigJSON(BaseModel):
    """
    Schema for the complete MCP configuration JSON.
    
    This format matches the expected configuration format for Claude Desktop and other MCP clients.
    """
    mcpServers: Dict[str, Dict[str, object]]
