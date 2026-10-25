import argparse
import os
import socket
import shlex
import zipfile
from dataclasses import dataclass, field
from pathlib import PurePosixPath

@dataclass
class Node:
    is_dir: bool
    data: bytes = b""
    owner: str = "root"
    children: dict[str, "Node"] = field(default_factory=dict)

class VirtualFileSystem:

    def __init__(self, archive_path: str | None):
        self.name = os.path.basename(archive_path or "default-vfs")
        self.root = Node(is_dir=True)
        self.cwd: tuple[str, ...] = ()

        if archive_path:
            self.load_zip(archive_path)

    @staticmethod
    def split_path(path: str) -> tuple[str, ...]:
        return tuple(
            part for part in path.replace("\\", "/").split("/")
            if part not in ("", ".")
        )

    def load_zip(self, archive_path: str) -> None:
        with zipfile.ZipFile(archive_path, "r") as archive:
            for item in archive.infolist():
                parts = self.split_path(item.filename)

                if not parts:
                    continue

                node = self.root

                for part in parts[:-1]:
                    node = node.children.setdefault(part, Node(True))

                name = parts[-1]

                if item.is_dir():
                    node.children.setdefault(name, Node(True))
                else:
                    node.children[name] = Node(
                        is_dir=False,
                        data=archive.read(item),
                    )

    def resolve(self, path: str = ".") -> tuple[str, ...]:
        parts = [] if path.startswith("/") else list(self.cwd)

        for part in self.split_path(os.path.expandvars(path)):
            if part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)

        return tuple(parts)

    def get_node(self, path: str = ".") -> Node:
        node = self.root

        for part in self.resolve(path):
            if not node.is_dir or part not in node.children:
                raise FileNotFoundError(f"Virtual path not found: {path}")
            node = node.children[part]

        return node
    
    def parent_and_name(self, path: str) -> tuple[Node, str]:
        parts = list(self.resolve(path))

        if not parts:
            raise ValueError("Cannot replace the VFS root")

        name = parts.pop()
        parent_path = "/" + "/".join(parts)
        parent = self.get_node(parent_path)

        if not parent.is_dir:
            raise NotADirectoryError(parent_path)

        return parent, name

    def mkdir(self, path: str) -> None:
        parent, name = self.parent_and_name(path)

        if name in parent.children:
            raise FileExistsError(path)

        parent.children[name] = Node(is_dir=True)

    def chown(self, owner: str, path: str) -> None:
        node = self.get_node(path)
        node.owner = owner

class Shell:
    def __init__(self, vfs: VirtualFileSystem):
        self.vfs = vfs
        self.running = True

    def prompt(self) -> str:
        user = os.environ.get("USERNAME", "user")
        host = socket.gethostname()
        path = "/" + "/".join(self.vfs.cwd)
        return f"{user}@{host}:{self.vfs.name}:{path}$ "

    def execute(self, line: str) -> bool:
        line = os.path.expandvars(line)

        try:
            args = shlex.split(line)
        except ValueError as error:
            print(f"Parse error: {error}")
            return False

        if not args:
            return True

        command, *params = args

        try:
            if command == "exit":
                self.running = False
            elif command == "ls":
                self.cmd_ls(params)
            elif command == "cd":
                self.cmd_cd(params)
            elif command == "echo":
                self.cmd_echo(params)
            elif command == "cat":
                self.cmd_cat(params)
            elif command == "wc":
                self.cmd_wc(params)
            elif command == "mkdir":
                  self.cmd_mkdir(params)
            elif command == "chown":
                  self.cmd_chown(params)
            elif command == "help":
                 self.cmd_help(params)
            else:
                print(f"Unknown command: {command}")
                return False
            
        except (
            FileNotFoundError,
            NotADirectoryError,
            FileExistsError,
            ValueError,
        ) as error:
            print(f"Error: {error}")
            return False

        return True

    def cmd_ls(self, params: list[str]) -> None:
        if len(params) > 1:
            raise ValueError("Usage: ls [PATH]")

        path = params[0] if params else "."
        node = self.vfs.get_node(path)

        if node.is_dir:
            print("  ".join(sorted(node.children)))
        else:
            print(PurePosixPath(path).name)

    def cmd_cd(self, params: list[str]) -> None:
        if len(params) > 1:
            raise ValueError("Usage: cd [PATH]")

        path = params[0] if params else "/"
        target = self.vfs.resolve(path)
        node = self.vfs.get_node(path)

        if not node.is_dir:
            raise NotADirectoryError(path)

        self.vfs.cwd = target

    def cmd_echo(self, params: list[str]) -> None:
        print(" ".join(params))

    def cmd_cat(self, params: list[str]) -> None:
        if len(params) != 1:
            raise ValueError("Usage: cat FILE")

        node = self.vfs.get_node(params[0])

        if node.is_dir:
            raise ValueError(f"Is a directory: {params[0]}")

        print(node.data.decode("utf-8"), end="")

    def cmd_wc(self, params: list[str]) -> None:
        mode = "all"

        if params and params[0] in ("-l", "-w", "-c"):
            mode = params[0][1:]
            params = params[1:]

        if len(params) != 1:
            raise ValueError("Usage: wc [-l|-w|-c] FILE")

        path = params[0]
        node = self.vfs.get_node(path)

        if node.is_dir:
            raise ValueError(f"Is a directory: {path}")

        text = node.data.decode("utf-8", errors="replace")
        counts = {
            "l": text.count("\n"),
            "w": len(text.split()),
            "c": len(node.data),
        }

        if mode == "all":
            result = f"{counts['l']} {counts['w']} {counts['c']}"
        else:
            result = str(counts[mode])

        print(f"{result} {path}")

    def cmd_mkdir(self, params: list[str]) -> None:
        if len(params) != 1:
            raise ValueError("Usage: mkdir PATH")

        self.vfs.mkdir(params[0])

    def cmd_chown(self, params: list[str]) -> None:
        if len(params) != 2:
            raise ValueError("Usage: chown OWNER PATH")

        owner, path = params
        self.vfs.chown(owner, path)
        print(f"Owner of {path} set to {owner} (in memory)")

    def cmd_help(self, params: list[str]) -> None:
        if params:
            raise ValueError("Usage: help")

        commands = [
            "ls [PATH] - list files and directories",
            "cd [PATH] - change current directory",
            "wc [-l|-w|-c] FILE - count lines, words, or bytes",
            "echo [TEXT ...] - print text",
            "cat FILE - print a text file",
            "mkdir PATH - create a virtual directory",
            "chown OWNER PATH - change virtual owner metadata",
            "help - show this help",
            "exit - quit the shell",
        ]

        print("\n".join(commands))
    
VFS_NAME = "default-vfs"


def prompt() -> str:
    user = os.environ.get("USERNAME", "user")
    host = socket.gethostname()
    return f"{user}@{host}:{VFS_NAME}:/ $ "



def run_script(shell: Shell, path: str) -> int:
    try:
        with open(path, "r", encoding="utf-8") as script:
            for number, raw_line in enumerate(script, 1):
                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                print(shell.prompt() + line)

                if not shell.execute(line):
                    print(f"Script stopped at line {number}")
                    return 1

                if not shell.running:
                    return 0
    except OSError as error:
        print(f"Cannot read script: {error}")
        return 1

    return 0


def repl(shell: Shell) -> None:
    while shell.running:
        try:
            line = input(shell.prompt())
        except (EOFError, KeyboardInterrupt):
            print()
            return

        shell.execute(line)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="In-memory VFS shell emulator"
    )
    parser.add_argument("--vfs", required=True)
    parser.add_argument("--script")
    args = parser.parse_args()

    print(f"Configuration: vfs={args.vfs}, script={args.script}")

    try:
        vfs = VirtualFileSystem(args.vfs)
    except (OSError, zipfile.BadZipFile) as error:
        print(f"Cannot load VFS: {error}")
        return

    shell = Shell(vfs)

    if args.script:
        raise SystemExit(run_script(shell, args.script))

    repl(shell)


if __name__ == "__main__":
    main()
