from abc import ABC
from git import Repo
import gitlab
import os
import argparse
import getpass
import contextlib

from utils import *

from typing import Tuple


class SyncedRepo(ABC):
    def __init__(
        self,
        url_or_hash: str,
        target_dir: str = None,
    ) -> None:
        self.input_url_or_hash = url_or_hash
        self.input_dir = target_dir

        self.www_url = None
        self.git_url = None
        self.hash = None
        self.download_directory = None
        self.new_directory = None
        self.directory = None
        self.download_success = False
        self.title = None
        self.hyphenated_title = None
        self.snakestyle_title = None

        self.www_url, self.git_url, self.hash = self._parse_input()

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
            Repo.clone_from(self.git_url, self.target_directory)
            self.download_success = True
        except Exception as e:
            print(f"An exception occurred: {e}")

    def get_title(self) -> None:
        self.title = get_title_from_LaTeX_project(self.target_directory)
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
        response = gl.projects.create({
            "name": self.title,
            "path": self.hash,
        })

    def add_GitLab_remote(self) -> None:
        with contextlib.chdir(self.directory):
            os.system(f"git remote add gitlab git@gitlab.com:deyanmihaylov/{self.hash}.git")
            os.system(f"git remote set-url origin --add --push https://git.overleaf.com/{self.hash}")
            os.system(f"git remote set-url origin --add --push git@gitlab.com:deyanmihaylov/{self.hash}.git")
        
    def push_to_GitLab(self) -> None:
        with contextlib.chdir(self.directory):
            os.system("git push gitlab")

    def __call__(self) -> None:
        self.download_Overleaf_project()
        self.get_title()
        self.rename_directory()
        self.create_empty_GitLab_repo()
        self.add_GitLab_remote()
        self.push_to_GitLab()


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
    
    # with open("./secret.txt", "r") as f: gitlab_token = f.read().strip()
    
    # gl = gitlab.Gitlab("https://gitlab.com/", private_token=gitlab_token, api_version=4)
    # gl.auth()

    # title = get_title_from_project(target_directory)
    # title_hyphenated = hyphenate_string(title)

    # response = gl.projects.create({
    #     "name": title,
    #     "path": hash_slug,
    # })

    # new_directory = os.path.join("/Users/deyanmihaylov/Documents/Work/Papers", title)

    # rename_folder(target_directory, new_directory)

    # os.chdir(new_directory)

    # add_GitLab_remote()
    # push_to_GitLab()

