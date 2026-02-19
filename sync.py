from abc import ABC
from git import Repo
import gitlab
import os
from pathlib import Path
import argparse
import getpass
import shutil
import logging
from pylatexenc.latex2text import LatexNodes2Text

from typing import Tuple, Optional

from utils import (
    run, get_urls_and_hash, get_title_from_LaTeX_project,
    hyphenate_string, snakestyle_string,
    rename_folder,
)


logger = logging.getLogger(__name__)


class SyncedRepo(ABC):
    def __init__(
        self,
        url_or_hash: str,
        target_dir: str | Path,
    ) -> None:
        """
        Create a sync session for one Overleaf project.

        Args:
            url_or_hash: Overleaf project URL (web or git) or project hash.
            target_dir: Existing directory where the project will be cloned.

        Raises:
            ValueError: If `target_dir` is None.
            NotADirectoryError: If `target_dir` is not an existing directory.
        """
        self.input_url_or_hash = url_or_hash

        if target_dir is None:
            raise ValueError("The target directory cannot be None")
        
        self.input_dir = Path(target_dir)
        if not self.input_dir.is_dir():
            raise NotADirectoryError(f"{self.input_dir} is not a directory")

        # Parse input early (hash is required to build paths)
        self.overleaf_web_url: Optional[str]
        self.overleaf_git_url: Optional[str]
        self.hash: str
        (
            self.overleaf_web_url,
            self.overleaf_git_url,
            self.hash,
        ) = self._parse_input()

        # Paths (Path objects)
        self.target_directory: Path = self.input_dir / self.hash
        self.directory: Path = self.target_directory
        self.new_directory: Optional[Path] = None

        # GitLab
        self.gitlab_web_url: Optional[str] = None
        self.gitlab_ssh_url: Optional[str] = None
        self.response = None

        # Metadata
        self.download_success: bool = False
        self.title: Optional[str] = None
        self.hyphenated_title: Optional[str] = None
        self.snakestyle_title: Optional[str] = None

        # Repo root (so running from another cwd works)
        self.repo_root: Path = Path(__file__).resolve().parent

    def _parse_input(self) -> Tuple[str, str, str]:
        return get_urls_and_hash(self.input_url_or_hash)

    def download_Overleaf_project(self) -> None:
        try:
            Repo.clone_from(self.overleaf_git_url, self.target_directory)
            self.download_success = True
        except Exception as e:
            logger.exception("Failed to clone Overleaf project: %s", e)
            raise

    def get_title(self) -> None:
        self.title = get_title_from_LaTeX_project(str(self.target_directory))
        self.title = LatexNodes2Text().latex_to_text(self.title)
        self.title = self.title.replace(":", "").replace(",", "")

        self.hyphenated_title = hyphenate_string(self.title)
        self.snakestyle_title = snakestyle_string(self.title)

    def rename_directory(self) -> None:
        if not self.snakestyle_title:
            raise ValueError(
                "snakestyle_title is not set; call get_title() first."
            )

        self.new_directory = self.input_dir / self.snakestyle_title
        rename_folder(
            str(self.directory), str(self.new_directory),
            exist_ok=False,
        )
        self.directory = self.new_directory

    def create_empty_GitLab_repo(self):
        if "GITLAB_OVERLEAF" in os.environ:
            gitlab_token = os.getenv("GITLAB_OVERLEAF")
        else:
            try:
                with open("./secret.txt", "r") as f:
                    gitlab_token = f.read().strip()
            except BaseException as e:
                gitlab_token = getpass.getpass("Enter GitLab access token:\n")
                os.environ["GITLAB_OVERLEAF"] = gitlab_token

        gl = gitlab.Gitlab(
            "https://gitlab.com/",
            private_token=gitlab_token,
            api_version=4,
        )
        gl.auth()
        self.response = gl.projects.create({
            "name": self.title,
            "path": self.hash,
        })

        self.gitlab_web_url = self.response.web_url
        self.gitlab_ssh_url = self.response.ssh_url_to_repo

    def add_GitLab_remote(self) -> None:
        # Add gitlab remote (if it already exists, you may want to handle that later)
        run(["git", "remote", "add", "gitlab", self.gitlab_ssh_url], cwd=self.directory)

        # Configure origin push URLs to include both Overleaf and GitLab
        run(
            ["git", "remote", "set-url", "origin", "--add", "--push", self.overleaf_git_url],
            cwd=self.directory,
        )
        run(
            ["git", "remote", "set-url", "origin", "--add", "--push", self.gitlab_ssh_url],
            cwd=self.directory,
        )
        
    def push_to_GitLab(self) -> None:
        run(["git", "push", "gitlab"], cwd=self.directory)

    def commit(self, message: str) -> None:
        run(["git", "commit", "-m", message], cwd=self.directory)

    def push(self) -> None:
        run(["git", "push"], cwd=self.directory)

    def add_GitLab_CI(self) -> None:
        shutil.copyfile(
            os.path.join(self.cwd, "src/sample_gitlab_CI.yml"),
            os.path.join(self.directory, ".gitlab-ci.yml"),
        )
        run(["git", "add", ".gitlab-ci.yml"], cwd=self.directory)

    def add_Readme(self) -> None:
        readme_path = os.path.join(self.directory, "README.md")
        with open(readme_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(f"[Latest manuscript](https://deyanmihaylov.gitlab.io/{self.hash}/main.pdf)\n")

        run(["git", "add", "README.md"], cwd=self.directory)

    def __call__(self) -> None:
        print("Cloning the repository from Overleaf")
        self.download_Overleaf_project()

        print("Extracting the project title:")
        self.get_title()
        print(self.title)

        print("Renaming the project directory")
        self.rename_directory()

        print("Creating a new GitLab repository")
        self.create_empty_GitLab_repo()

        print("Linking the local repository to the new GitLab repository")
        self.add_GitLab_remote()

        print("Pushing to the new GitLab repository")
        self.push_to_GitLab()

        self.add_GitLab_CI()
        self.commit("Add GitLab CI")
        self.push()

        self.add_Readme()
        self.commit("Add Readme.md")
        self.push()

        # add setup.sh


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="OverleafToGitLab")
    parser.add_argument("url_or_hash")
    parser.add_argument("--dir", default=os.getcwd())
    args = parser.parse_args()

    sync = SyncedRepo(
        url_or_hash = args.url_or_hash,
        target_dir = args.dir,
    )
    sync()
