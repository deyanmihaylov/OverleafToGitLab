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
        url_or_hash: str,
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

def get_urls_and_hash(url_or_hash):
    """
    https://www.overleaf.com/project/5cfacaa5a39cd676c26e6332
    https://git.overleaf.com/5cfacaa5a39cd676c26e6332
    5cfacaa5a39cd676c26e6332
    """
    if url_or_hash[:33] == "https://www.overleaf.com/project/":
        www_url = url_or_hash
        git_url = url_or_hash.replace(
            "https://www.overleaf.com/project/", "https://git.overleaf.com/",
        )
        hash_slug = url_or_hash.replace(
            "https://www.overleaf.com/project/", '',
        )
    elif url_or_hash[:25] == "https://git.overleaf.com/":
        www_url = url_or_hash.replace(
            "https://git.overleaf.com/", "https://www.overleaf.com/project/",
        )
        git_url = url_or_hash
        hash_slug = url_or_hash.replace(
            "https://git.overleaf.com/", '',
        )
    elif url_or_hash.isalnum():
        www_url = f"https://www.overleaf.com/project/{url_or_hash}"
        git_url = f"https://git.overleaf.com/{url_or_hash}"
        hash_slug = url_or_hash
    else:
        raise Exception("URL not recognised")

    return www_url, git_url, hash_slug


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="OverleafToGitLab")
    # parser.add_argument("--url", default=None)
    # parser.add_argument("--hash", default=None)
    parser.add_argument("url_or_hash")
    parser.add_argument("--dir", default="/Users/deyanmihaylov/Documents/Work/Papers")
    args = parser.parse_args()

    print(args.url_or_hash)
    for x in get_urls_and_hash(args.url_or_hash):
        print(x)
    exit()

    sync = SyncedRepo(
        url_or_hash=args.url_or_hash,
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

