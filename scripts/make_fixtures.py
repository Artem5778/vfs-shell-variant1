import sys
import zipfile
from pathlib import Path


FIXTURES = {
    "minimal": {
        "readme.txt": "Hello, VFS!\n",
    },
    "full": {
        "readme.txt": "VFS shell example\n",
        "docs/guide.txt": "Guide content\n",
        "data/values.txt": "10 20 30\n",
    },
    "deep": {
        "level1/level2/level3/file.txt": "Deep file\n",
    },
}


def main() -> None:
    output = Path(".test-vfs")
    output.mkdir(exist_ok=True)
    names = sys.argv[1:] or list(FIXTURES)

    for name in names:
        if name not in FIXTURES:
            raise SystemExit(f"Unknown fixture: {name}")

        archive_path = output / f"{name}.zip"

        with zipfile.ZipFile(archive_path, "w") as archive:
            for path, content in FIXTURES[name].items():
                archive.writestr(path, content)

        print(f"Created {archive_path}")


if __name__ == "__main__":
    main()