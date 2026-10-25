import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "src" / "main.py"


class ShellTests(unittest.TestCase):

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.archive = Path(self.temp_dir.name) / "test.zip"

        with zipfile.ZipFile(self.archive, "w") as archive:
            archive.writestr("readme.txt", "hello world\n")
            archive.writestr("docs/guide.txt", "line one\nline two\n")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_shell(self, commands: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(MAIN),
                "--vfs",
                str(self.archive),
            ],
            input=commands,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_help(self) -> None:
        result = self.run_shell("help\nexit\n")
        self.assertIn("mkdir", result.stdout)

    def test_list_and_change_directory(self) -> None:
        result = self.run_shell("ls\ncd docs\nls\nexit\n")
        self.assertIn("readme.txt", result.stdout)
        self.assertIn("guide.txt", result.stdout)

    def test_cat_and_wc(self) -> None:
        result = self.run_shell("cat readme.txt\nwc -w readme.txt\nexit\n")
        self.assertIn("hello world", result.stdout)
        self.assertIn("2 readme.txt", result.stdout)

    def test_mkdir_and_chown(self) -> None:
        result = self.run_shell(
            "mkdir newdir\nls\nchown student readme.txt\nexit\n"
        )
        self.assertIn("newdir", result.stdout)
        self.assertIn("student", result.stdout)

    def test_unknown_command(self) -> None:
        result = self.run_shell("unknown_command\nexit\n")
        self.assertIn("Unknown command", result.stdout)


if __name__ == "__main__":
    unittest.main()