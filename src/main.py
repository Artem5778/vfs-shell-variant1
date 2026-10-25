import os
import socket
import shlex


VFS_NAME = "default-vfs"


def prompt() -> str:
    user = os.environ.get("USERNAME", "user")
    host = socket.gethostname()
    return f"{user}@{host}:{VFS_NAME}:/ $ "


def execute(line: str) -> bool:
    line = os.path.expandvars(line)

    try:
        args = shlex.split(line)
    except ValueError as error:
        print(f"Parse error: {error}")
        return True

    if not args:
        return True

    command = args[0]
    params = args[1:]

    if command == "exit":
        return False

    if command == "ls":
        print("ls: command is not implemented yet")
    elif command == "cd":
        print("cd: command is not implemented yet")
    else:
        print(f"Unknown command: {command}")

    return True


def main() -> None:
    running = True

    while running:
        try:
            line = input(prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            break

        running = execute(line)


if __name__ == "__main__":
    main()