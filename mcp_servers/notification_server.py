"""Notification System MCP Server - Handles notifications for loan decisions (SQLite-backed)."""
import logging
from datetime import datetime

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from common.config import NOTIFICATION_PORT
from common import db

logger = logging.getLogger(__name__)
mcp = FastMCP("notification")

db.init_db()


@mcp.custom_route("/health", methods=["GET"])
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "notification_system"})


@mcp.tool()
def send_notification(case_id: str, notification_type: str, recipient: str, subject: str, message: str) -> dict:
    """Send (and persist) a notification for a loan decision."""
    timestamp = datetime.utcnow().isoformat()
    notification_id = db.save_notification(
        case_id, notification_type, recipient, subject, message, timestamp, "sent"
    )
    logger.info(f"Notification sent for case {case_id}: {subject}")
    print(f"[NOTIFICATION] {notification_type} to {recipient}: {subject}")

    return {
        "success": True,
        "case_id": case_id,
        "notification_id": notification_id,
        "message": "Notification sent successfully"
    }


@mcp.tool()
def get_notifications(case_id: str | None = None) -> dict:
    """Retrieve notifications, optionally filtered by case_id."""
    if case_id:
        case_notifications = db.get_notifications(case_id)
        return {
            "success": True,
            "case_id": case_id,
            "notifications": case_notifications
        }

    all_notifications = db.get_notifications()
    return {
        "success": True,
        "total_notifications": len(all_notifications),
        "notifications": all_notifications
    }


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=NOTIFICATION_PORT)
