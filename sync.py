from abc import ABC

import subprocess
from git import Repo
import gitlab
import os
from pathlib import Path
import argparse
import getpass
import shutil
import logging
from pylatexenc.latex2text import LatexNodes2Text

from utils import (
    run, get_urls_and_hash, get_title_from_LaTeX_project,
    slugify,
    rename_folder,
)

from typing import Tuple, Optional, Union

PathLike = Union[str, Path]


logger = logging.getLogger(__name__)


class SyncedRepo(ABC):
    def __init__(
        self,
        url_or_hash: str,
        target_dir: PathLike,
    ) -> None:
        """Create a sync session for one Overleaf project.

        Args:
            url_or_hash: Overleaf project URL (web or git) or project hash.
            target_dir: Existing directory where the project will be cloned.

        Raises:
            ValueError: If `target_dir` is None.
            NotADirectoryError: If `target_dir` is not an existing directory.
        """
        if target_dir is None:
            raise ValueError("The target directory cannot be None")

        self.input_url_or_hash = url_or_hash
        self.input_dir = Path(target_dir)

        if not self.input_dir.is_dir():
            raise NotADirectoryError(f"{self.input_dir} is not a directory")

        # Repo root (so running from another cwd works)
        self.repo_root: Path = Path(__file__).resolve().parent

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

    def _parse_input(self) -> Tuple[str, str, str]:
        """Parse Overleaf identifier into (web_url, git_url, hash)."""
        return get_urls_and_hash(self.input_url_or_hash)

    def download_Overleaf_project(self) -> None:
        """
        Clone the Overleaf repository into the target directory.

        This method performs a shallow clone of the Overleaf git repository
        specified by `self.overleaf_git_url` into `self.target_directory`.

        Side Effects:
            - Creates a new local git repository on disk.
            - Sets `self.download_success = True` on success.

        Raises:
            ValueError: If the Overleaf git URL is not set.
            GitCommandError: If cloning fails (network issues, auth failure, etc.).
            OSError: If the target directory cannot be written.
        """
        if not self.overleaf_git_url:
            raise ValueError("overleaf_git_url is not set")

        logger.info("Cloning Overleaf repo into %s", self.target_directory)

        Repo.clone_from(self.overleaf_git_url, self.target_directory)
        self.download_success = True

    def _get_title(self) -> None:
        """
        Extract title from LaTeX sources and derive slug variants.

        If no \\title{...} is found, falls back to using the project hash.
        """
        raw_title = get_title_from_LaTeX_project(self.target_directory)

        if raw_title:
            title_text = LatexNodes2Text().latex_to_text(raw_title).strip()
        else:
            # Fallback: use the hash so the pipeline can still proceed
            title_text = self.hash

        self.title = title_text
        self.hyphenated_title = slugify(
            title_text, style="kebab", lowercase=False,
        )
        self.snakestyle_title = slugify(
            title_text, style="snake", lowercase=False,
        )

    # def rename_directory(self) -> None:
    #     if not self.snakestyle_title:
    #         raise ValueError(
    #             "snakestyle_title is not set; call get_title() first."
    #         )

    #     self.new_directory = self.input_dir / self.snakestyle_title
    #     rename_folder(
    #         str(self.directory), str(self.new_directory),
    #         exist_ok=False,
    #     )
    #     self.directory = self.new_directory

    def rename_directory(self) -> None:
        if not self.snakestyle_title:
            raise ValueError(
                "snakestyle_title is not set; call _get_title() first."
            )

        new_dir = self.input_dir / self.snakestyle_title
        rename_folder(self.directory, new_dir, exist_ok=False)
        self.directory = new_dir

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

    def commit(self, message: str, *, allow_empty: bool = False) -> None:
        """
        Commit staged changes in the repository.

        Args:
            message: Commit message.
            allow_empty: If True, do not raise when there is nothing to commit.

        Raises:
            subprocess.CalledProcessError: If the git command fails for reasons
                other than an empty commit (unless `allow_empty=True`).
        """
        try:
            run(["git", "commit", "-m", message], cwd=self.directory)
        except subprocess.CalledProcessError as e:
            if allow_empty:
                logger.info("No changes to commit: %s", message)
                return
            raise

    def push(self) -> None:
        run(["git", "push"], cwd=self.directory)

    def _commit_and_push(self, message: str) -> None:
        """Commit staged changes (if any) and push."""
        try:
            self.commit(message)
        except subprocess.CalledProcessError:
            # Most common cause: "nothing to commit"
            logger.info("Commit skipped (nothing to commit): %s", message)
            return
        self.push()

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
        """
        Sync an Overleaf project to a newly-created GitLab repository.

        This workflow:
        1) Clones the Overleaf git repository locally.
        2) Extracts the LaTeX title and computes slug variants.
        3) Renames the local directory based on the title slug.
        4) Creates an empty GitLab repository via the GitLab API.
        5) Adds a GitLab remote and configures push URLs.
        6) Pushes the repository to GitLab.
        7) Adds CI configuration and README, commits, and pushes.

        Raises:
            Exception: Propagates exceptions raised by underlying steps (git, IO,
                GitLab API). Fail-fast behavior is intentional for automation.
        """
        # Clone the repository from Overleaf to a local directory
        logger.info("Cloning the repository from Overleaf")
        self.download_Overleaf_project()

        # Get the project title from the .tex file
        logger.info("Extracting the project title")
        self._get_title()
        logger.info("Title: %s", self.title)

        # Rename the directory to the project title
        logger.info("Renaming the project directory")
        self.rename_directory()

        # Create a new repository on GitLab
        logger.info("Creating a new GitLab repository")
        self.create_empty_GitLab_repo()

        # Link the local (Overleaf) repository to the new GitLab repository
        logger.info("Linking the local repository to the new GitLab repository")
        self.add_GitLab_remote()

        # Push the project to the linked GitLab repository
        logger.info("Pushing to the new GitLab repository")
        self.push_to_GitLab()

        # Add a GitLab CI script for compiling the project
        logger.info("Adding GitLab CI configuration")
        self.add_GitLab_CI()
        self._commit_and_push("Add GitLab CI")

        # Add README file to the project
        logger.info("Adding README")
        self.add_Readme()
        self._commit_and_push("Add README.md")

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
