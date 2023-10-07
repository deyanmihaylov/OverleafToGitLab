import os
import glob
import re


def get_Overleaf_url_from_hash(hash_slug: str) -> str:
    url = f"https://git.overleaf.com/{hash_slug}"
    return url

def get_hash_from_Overleaf_url(url: str) -> str:
    hash_slug = url.rsplit('/', 1)[-1]
    return hash_slug

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
