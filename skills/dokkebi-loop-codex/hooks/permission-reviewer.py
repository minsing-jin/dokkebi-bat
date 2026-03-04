#!/usr/bin/env python3
import json
import sys


def emit(behavior: str, message: str = "") -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": behavior},
        }
    }
    if behavior == "deny" and message:
        output["hookSpecificOutput"]["decision"]["message"] = message
    sys.stdout.write(json.dumps(output))


def main() -> None:
    payload = json.load(sys.stdin)
    tool_name = payload.get("tool_name", "unknown")
    tool_input = payload.get("tool_input", {})

    # Deny modifications to sensitive dotenv files explicitly.
    if tool_name in {"Edit", "Write"}:
        path = str(tool_input.get("file_path", ""))
        if "/.env" in path or path.endswith(".env"):
            emit("deny", "editing dotenv files is blocked")
            return

    # Default to allow to avoid blocking normal development flow.
    emit("allow")


if __name__ == "__main__":
    main()
