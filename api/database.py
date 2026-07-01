from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from db_models.database import DatabaseConfig
from connectors.manager import connection_manager

from exception.exceptions import (
    DatabaseConnectionError,
    UnsupportedDatabaseError,
    DatabaseNotConnectedError,
    AuthenticationError,
)

router = APIRouter(
    prefix="/database",
    tags=["Database"],
)


class MessageResponse(BaseModel):
    success: bool
    message: str


############################################################
# CONNECT
############################################################


@router.post(
    "/connect",
    response_model=MessageResponse,
)
def connect_database(config: DatabaseConfig):

    try:

        connection_manager.connect(config)

        return MessageResponse(success=True, message="Database connected successfully.")

    except AuthenticationError as e:

        raise HTTPException(status_code=401, detail=str(e))

    except UnsupportedDatabaseError as e:

        raise HTTPException(status_code=400, detail=str(e))

    except DatabaseConnectionError as e:

        raise HTTPException(status_code=500, detail=str(e))


############################################################
# DISCONNECT
############################################################


@router.post(
    "/disconnect",
    response_model=MessageResponse,
)
def disconnect_database():

    connection_manager.disconnect()

    return MessageResponse(success=True, message="Database disconnected.")


############################################################
# STATUS
############################################################


@router.get("/status")
def database_status():

    if not connection_manager.is_connected():

        return {"connected": False}

    return {"connected": True, "database": connection_manager.current_database()}


############################################################
# TEST CONNECTION
############################################################


@router.post("/test")
def test_connection():

    try:

        return {"success": connection_manager.test_connection()}

    except DatabaseNotConnectedError as e:

        raise HTTPException(status_code=400, detail=str(e))


############################################################
# SWITCH DATABASE
############################################################


@router.post(
    "/switch",
    response_model=MessageResponse,
)
def switch_database(config: DatabaseConfig):

    try:

        connection_manager.switch_database(config)

        return MessageResponse(success=True, message="Database switched successfully.")

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))


############################################################
# CURRENT DATABASE INFO
############################################################


@router.get("/current")
def current_database():

    try:

        return connection_manager.current_database()

    except DatabaseNotConnectedError as e:

        raise HTTPException(status_code=400, detail=str(e))


############################################################
# LIST MONGO COLLECTIONS
############################################################


@router.get("/collections")
def list_collections():

    try:

        return {"collections": connection_manager.list_collections()}

    except UnsupportedDatabaseError as e:

        raise HTTPException(status_code=400, detail=str(e))

    except DatabaseNotConnectedError as e:

        raise HTTPException(status_code=400, detail=str(e))
