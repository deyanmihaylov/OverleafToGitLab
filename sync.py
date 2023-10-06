from git import Repo
import gitlab
import re
import os
import glob
import sys

def get_hash_from_url(url: str) -> str:
    hash = url.rsplit('/', 1)[-1]
    return hash

def get_title_from_project(directory: str) -> str:
    main_file = "main.tex"
    if os.path.isfile(os.path.join(directory, main_file)):
        title_line = extract_title_from_TeX_file(os.path.join(directory, main_file))
    else:
        for filepath in glob.glob(os.path.join(directory, "*.tex")):
            title_line = extract_title_from_TeX_file(filepath)
            if title_line != "":
                break
    title = get_title_from_latex_line(title_line)
    return title

def extract_title_from_TeX_file(filepath: str) -> str:
    with open(filepath, "r") as file:
        for line in file:
            if re.search(r"\\title", line):
                title_line = line
    return title_line.strip()

def get_title_from_latex_line(line: str) -> str:
    line = line.replace(r"\\title", '')
    first_bracket = line.find("{")
    last_bracket = line.rfind("}")
    return line[(first_bracket+1):last_bracket]

def hyphenate_string(string: str) -> str:
    string = re.sub(" +", ' ', string)
    string = string.replace(' ', '-')
    return string

def rename_folder(path: str, new_name: str) -> None:
    try:
        os.rename(path, new_name)
    except:
        sys.exit("rename_folder() failed")

def add_GitLab_remote() -> None:
    with os.chdir(new_directory):
        os.system(f"git remote add gitlab git@gitlab.com:deyanmihaylov/{hash_slug}.git")
        os.system(f"git remote set-url origin --add --push https://git.overleaf.com/{hash_slug}")
        os.system(f"git remote set-url origin --add --push git@gitlab.com:deyanmihaylov/{hash_slug}.git")

def push_to_GitLab() -> None:
    with os.chdir(new_directory):
        os.system("git push gitlab")


if __name__ == "__main__":
    url = "https://git.overleaf.com/626b9df2eca2e09002ab2ac3"
    hash_slug = get_hash_from_url(url)

    target_directory = os.path.join("/Users/deyanmihaylov/Documents/Work/Papers", hash_slug)
    Repo.clone_from(url, target_directory)
    
    with open("./secret.txt", "r") as f: gitlab_token = f.read().strip()
    
    gl = gitlab.Gitlab("https://gitlab.com/", private_token=gitlab_token, api_version=4)
    gl.auth()

    title = get_title_from_project(target_directory)
    title = hyphenate_string(title)

    response = gl.projects.create({
        "name": title,
        "path": hash_slug,
    })

    new_directory = os.path.join("/Users/deyanmihaylov/Documents/Work/Papers", title)

    rename_folder(target_directory, new_directory)

    os.chdir(new_directory)

    add_GitLab_remote()
    push_to_GitLab()

