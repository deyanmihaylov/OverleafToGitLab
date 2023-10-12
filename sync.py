from abc import ABC
from git import Repo
import gitlab
import os
from pathlib import Path
import argparse

from utils import *


class SyncedRepo(ABC):
    def __init__(
        self,
        url: str = None,
        hash_slug: str = None,
        target_dir: str = None,
    ) -> None:
        self.url = None
        self.hash = None
        self.download_directory = None
        self.new_directory = None
        self.directory = None
        self.download_success = False
        self.title = None
        self.hyphenated_title = None
        self.snakestyle_title = None

        if url is None and hash_slug is None:
            raise ValueError
        elif url is None:
            self.hash = hash_slug
            self.url = get_Overleaf_url_from_hash(self.hash)
        elif hash_slug is None:
            self.url = url
            self.hash = get_hash_from_Overleaf_url(self.url)
        else:
            raise ValueError

        if target_dir is None:
            raise ValueError
        else:
            if not os.path.isdir(target_dir):
                raise ValueError
            else:
                self.target_directory = os.path.join(target_dir, self.hash)
                self.directory = self.target_directory

    def download_Overleaf_project(self) -> None:
        try:
            Repo.clone_from(self.url, self.target_directory)
            self.download_success = True
        except Exception as e:
            print(f"An exception occurred: {e}")

    def get_title(self) -> None:
        self.title = get_title_from_LaTeX_project(self.target_directory)
        self.hyphenated_title = hyphenate_string(self.title)
        self.snakestyle_title = snakestyle_string(self.title)

    def rename_directory(self) -> None:
        self.new_directory = os.path.join(
            "/Users/deyanmihaylov/Documents/Work/Papers",
            self.snakestyle_title,
        )
        rename_folder(self.directory, self.new_directory)
        self.directory = self.new_directory

    def create_empty_GitLab_repo(self):
        try:
            with open("./secret.txt", "r") as f:
                gitlab_token = f.read().strip()
        except BaseException as e:
            gitlab_token = input("Enter GitLab access token:\n")

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
        with os.chdir(new_directory):
            os.system(f"git remote add gitlab git@gitlab.com:deyanmihaylov/{self.hash}.git")
            os.system(f"git remote set-url origin --add --push https://git.overleaf.com/{self.hash}")
            os.system(f"git remote set-url origin --add --push git@gitlab.com:deyanmihaylov/{self.hash}.git")
        
    def push_to_GitLab(self) -> None:
        with os.chdir(new_directory):
            os.system("git push gitlab")

    def __call__(self):
        self.download_Overleaf_project()
        self.get_title()
        self.rename_directory()
        self.create_empty_GitLab_repo()
        self.add_GitLab_remote()
        self.push_to_GitLab()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="OverleafToGitLab")
    # parser.add_argument("--url", default=None)
    # parser.add_argument("--hash", default=None)
    parser.add_argument("url_or_hash")
    parser.add_argument("--dir", default="/Users/deyanmihaylov/Documents/Work/Papers")
    args = parser.parse_args()

    sync = SyncedRepo(
        url=args.url,
        hash_slug=args.hash,
        target_dir=args.dir,
    )
    
    url = "https://git.overleaf.com/626b9df2eca2e09002ab2ac3"
    hash_slug = get_hash_from_url(url)

    target_directory = os.path.join("/Users/deyanmihaylov/Documents/Work/Papers", hash_slug)
    Repo.clone_from(url, target_directory)
    
    with open("./secret.txt", "r") as f: gitlab_token = f.read().strip()
    
    gl = gitlab.Gitlab("https://gitlab.com/", private_token=gitlab_token, api_version=4)
    gl.auth()

    title = get_title_from_project(target_directory)
    title_hyphenated = hyphenate_string(title)

    response = gl.projects.create({
        "name": title,
        "path": hash_slug,
    })

    new_directory = os.path.join("/Users/deyanmihaylov/Documents/Work/Papers", title)

    rename_folder(target_directory, new_directory)

    os.chdir(new_directory)

    add_GitLab_remote()
    push_to_GitLab()

