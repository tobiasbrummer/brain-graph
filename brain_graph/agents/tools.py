from typing import Any, Protocol


class Tool(Protocol):
    name: str
    trigger_status: str  # The status that triggers this tool

    def execute(self, file_path: str, content: str) -> str:
        """
        Executes the tool action.
        Returns a string to be appended to the file (feedback).
        """
        ...


class CalendarTool:
    name = "calendar_api"
    trigger_status = "schedule_meeting"

    def execute(self, file_path: str, content: str) -> str:
        # In a real implementation, this would parse the content for date/attendees
        # and call an API.
        return "\n\n> [!INFO] Calendar Invite sent (Mock).\n"


class MailTool:
    name = "mail_api"
    trigger_status = "send_mail"

    def execute(self, file_path: str, content: str) -> str:
        return "\n\n> [!INFO] Mail sent (Mock).\n"


TOOL_REGISTRY = {
    "calendar_api": CalendarTool(),
    "mail_api": MailTool(),
}


def get_tool(name: str) -> Tool | None:
    return TOOL_REGISTRY.get(name)
