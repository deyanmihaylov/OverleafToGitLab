from abc import ABC
from git import Repo
import gitlab
import os
import argparse
import getpass
import shutil
from pylatexenc.latex2text import LatexNodes2Text

from typing import Tuple

from utils import *


class SyncedRepo(ABC):
    def __init__(
        self,
        url_or_hash: str,
        target_dir: str = None,
    ) -> None:
        self.input_url_or_hash = url_or_hash
        self.input_dir = target_dir

        self.overleaf_web_url = None
        self.overleaf_git_url = None
        self.gitlab_web_url = None
        self.gitlab_ssh_url = None
        self.hash = None
        self.download_directory = None
        self.new_directory = None
        self.directory = None
        self.cwd = os.getcwd()
        self.download_success = False
        self.title = None
        self.hyphenated_title = None
        self.snakestyle_title = None

        (
            self.overleaf_web_url,
            self.overleaf_git_url,
            self.hash,
        ) = self._parse_input()

        if self.input_dir is None:
            raise Exception("The target directory cannot be None")
        elif not os.path.isdir(self.input_dir):
            raise Exception(f"{self.input_dir} is not a directory")
        else:
            self.target_directory = os.path.join(self.input_dir, self.hash)
            self.directory = self.target_directory

    def _parse_input(self) -> Tuple[str, str, str]:
        return get_urls_and_hash(self.input_url_or_hash)

    def download_Overleaf_project(self) -> None:
        try:
            Repo.clone_from(self.overleaf_git_url, self.target_directory)
            self.download_success = True
        except Exception as e:
            print(f"An exception occurred: {e}")

    def get_title(self) -> None:
        self.title = get_title_from_LaTeX_project(self.target_directory)
        self.title = LatexNodes2Text().latex_to_text(self.title)
        self.title = self.title.replace(':', '')
        
        self.hyphenated_title = hyphenate_string(self.title)
        self.snakestyle_title = snakestyle_string(self.title)

    def rename_directory(self) -> None:
        self.new_directory = os.path.join(
            self.input_dir, self.snakestyle_title,
        )
        rename_folder(self.directory, self.new_directory)
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
        os.chdir(self.directory)
        os.system(
            f"git remote add gitlab {self.gitlab_ssh_url}"
        )
        os.system(
            f"git remote set-url origin --add --push {self.overleaf_git_url}"
        )
        os.system(
            f"git remote set-url origin --add --push {self.gitlab_ssh_url}"
        )
        os.chdir(self.cwd)
        
    def push_to_GitLab(self) -> None:
        os.chdir(self.directory)
        os.system("git push gitlab")
        os.chdir(self.cwd)

    def commit(self, message: str) -> None:
        os.chdir(self.directory)
        os.system(f"git commit -m \"{message}\"")
        os.chdir(self.cwd)

    def push(self) -> None:
        os.chdir(self.directory)
        os.system("git push")
        os.chdir(self.cwd)

    def add_GitLab_CI(self) -> None:
        shutil.copyfile(
            os.path.join(self.cwd, "src/sample_gitlab_CI.yml"),
            os.path.join(self.directory, ".gitlab-ci.yml"),
        )
        os.chdir(self.directory)
        os.system(f"git add .gitlab-ci.yml")
        os.chdir(self.cwd)

    def add_Readme(self) -> None:
        shutil.copyfile(
            os.path.join(self.cwd, "src/sample_README.md"),
            os.path.join(self.directory, "README.md"),
        )
        os.chdir(self.directory)
        os.system(f"git add README.md")
        os.chdir(self.cwd)

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
