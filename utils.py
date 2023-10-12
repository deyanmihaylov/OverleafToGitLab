import os
import glob
import re

from typing import Tuple


def get_urls_and_hash(url_or_hash: str) -> Tuple[str, str, str]:
    """
    url_or_hash can be of the form of any of the below 3:
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

def get_title_from_LaTeX_project(directory: str) -> str:
    main_file = "main.tex"
    if os.path.isfile(os.path.join(directory, main_file)):
        title_line = extract_title_from_TeX_file(os.path.join(directory, main_file))
    else:
        for filepath in glob.glob(os.path.join(directory, "*.tex")):
            title_line = extract_title_from_TeX_file(filepath)
            if title_line != "":
                break
    title = get_title_from_LaTeX_line(title_line)
    return title

def extract_title_from_TeX_file(filepath: str) -> str:
    with open(filepath, "r") as file:
        for line in file:
            if re.search(r"\\title", line):
                title_line = line
                break
    return title_line.strip()

def get_title_from_LaTeX_line(line: str) -> str:
    line = line.replace(r"\\title", '')
    first_bracket = line.find("{")
    last_bracket = line.rfind("}")
    return line[(first_bracket+1):last_bracket]

def hyphenate_string(string: str) -> str:
    string = re.sub(" +", ' ', string)
    string = string.replace(' ', '-')
    return string

def snakestyle_string(string: str) -> str:
    string = re.sub(" +", ' ', string)
    string = string.replace(' ', '_')
    return string

def rename_folder(path: str, new_name: str) -> None:
    try:
        os.rename(path, new_name)
    except Exception as e:
        print(f"An exception occurred: {e}")


if __name__ == "__main__":
    pass
