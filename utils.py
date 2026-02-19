import os
import glob
import re
# import sys
import subprocess
from pathlib import Path
import logging

from typing import Tuple, Sequence


logger = logging.getLogger(__name__)


OVERLEAF_WEB_PREFIX = "https://www.overleaf.com/project/"
OVERLEAF_GIT_PREFIX = "https://git.overleaf.com/"


def run(cmd: Sequence[str], cwd: str | None = None) -> None:
    """
    Execute a command safely and raise if it fails.

    Parameters
        cmd : list[str]
            Command and arguments, e.g. ["git", "push", "origin", "main"].
        cwd : str | None
            Working directory.
    """
    print(">>", " ".join(cmd))
    subprocess.run(cmd, cwd=cwd, check=True)

def get_urls_and_hash(url_or_hash: str) -> Tuple[str, str, str]:
    """
    Parse an Overleaf identifier and return canonical URLs.

    The input may be:
        - Overleaf web URL:
            https://www.overleaf.com/project/<hash>
        - Overleaf git URL:
            https://git.overleaf.com/<hash>
        - Raw project hash:
            <hash>

    Args:
        url_or_hash: Overleaf project web URL, git URL, or hash.

    Returns:
        Tuple[str, str, str]:
            (web_url, git_url, project_hash)

    Raises:
        ValueError: If the input cannot be interpreted as a valid
            Overleaf project identifier.
    """
    if not url_or_hash:
        raise ValueError("Empty Overleaf identifier")
    
    value = url_or_hash.strip().rstrip("/")
    
    if value.startswith(OVERLEAF_WEB_PREFIX):
        # Case 1: Overleaf web URL
        hash_slug = value.removeprefix(OVERLEAF_WEB_PREFIX)
    elif value.startswith(OVERLEAF_GIT_PREFIX):
        # Case 2: Overleaf git URL
        hash_slug = value.removeprefix(OVERLEAF_GIT_PREFIX)
    else:
        # Case 3: Raw hash
        hash_slug = value

    # Basic validation of project hash
    # Overleaf hashes are alphanumeric (usually hex-like)
    if not hash_slug or not hash_slug.isalnum():
        raise ValueError(f"Unrecognised Overleaf identifier: {url_or_hash}")
    
    www_url = f"{OVERLEAF_WEB_PREFIX}{hash_slug}"
    git_url = f"{OVERLEAF_GIT_PREFIX}{hash_slug}"
    
    return www_url, git_url, hash_slug

def get_title_from_LaTeX_project(directory: str) -> str:
    main_file = "main.tex"
    if os.path.isfile(os.path.join(directory, main_file)):
        title_line = extract_title_from_TeX_file(
            os.path.join(directory, main_file)
        )
    else:
        for filepath in glob.glob(os.path.join(directory, "*.tex")):
            title_line = extract_title_from_TeX_file(filepath)
            if title_line != "":
                break
    title = get_title_from_LaTeX_line(title_line)
    return title

def extract_title_from_TeX_file(filepath: str) -> str:
    file_contents = ''
    with open(filepath, 'r') as file:
        for line in file:
            comment_char_idxs = character_idxs(line, '%')
            entire_line_is_commented = False
            comment_start = -1

            for idx in comment_char_idxs:
                if idx == 0:
                    # Entire line is commented out
                    entire_line_is_commented = True
                    break
                elif line[idx-1] == '\\':
                    # This comment characted is escaped
                    continue
                else:
                    # This is where the comment on this line begins
                    comment_start = idx
                    break

            if entire_line_is_commented: continue
            file_contents += line[0:comment_start].strip()
    
    title_location = file_contents.find("\\title")
    if title_location == -1:
        return ''
    else:
        return extract_first_latex_command(file_contents[title_location:])

def extract_first_latex_command(string: str):
    count_opening_curly = 0
    count_closing_curly = 0

    i = 0

    while True:
        if string[i] == '{':
            if i != 0 and string[i-1] == '\\':
                # This opening curly bracket is escaped
                pass
            else:
                # We have an opening curly bracket
                count_opening_curly += 1
        else:
            pass

        if string[i] == '}':
            if i == 0:
                # String starts with closing curly bracket
                raise ValueError
            elif string[i-1] == '\\':
                # This closing curly bracket is escaped
                pass
            else:
                # We have a closing curly bracket
                count_closing_curly += 1
        else:
            pass
        
        i += 1

        if count_opening_curly > 0 and count_opening_curly == count_closing_curly:
            break

    return string[:i]

def character_idxs(string: str, match: str):
    return [idx for idx, c in enumerate(string) if c == match]

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
    """
    Replace intervals in a string with underscores

    Args:
        string (str): the string whose intervals will be replaced

    Returns:
        str: the original string with intervals replaced with underscores
    """
    string = re.sub(" +", ' ', string)
    string = string.replace(' ', '_')
    return string

def rename_folder(
    path: str,
    new_name: str,
    *,
    exist_ok: bool = False,
) -> None:
    """
    Rename a directory.

    Args:
        path: Existing directory path.
        new_name: New directory path.
        exist_ok: If True, do nothing when the destination already exists.
            This makes the operation idempotent for repeated sync runs.

    Returns:
        None

    Raises:
        FileNotFoundError: If the source directory does not exist.
        NotADirectoryError: If the source path is not a directory.
        FileExistsError: If the target directory already exists and
            `exist_ok` is False.
        OSError: If the rename operation fails at the OS level.
    """
    src = Path(path)
    dst = Path(new_name)

    if not src.exists():
        raise FileNotFoundError(f"Source directory does not exist: {src}")

    if not src.is_dir():
        raise NotADirectoryError(f"Source is not a directory: {src}")

    if dst.exists():
        if exist_ok:
            logger.info("Directory already named '%s'; skipping rename.", dst.name)
            return
        raise FileExistsError(f"Target directory already exists: {dst}")

    logger.info("Renaming directory: %s -> %s", src, dst)
    src.rename(dst)


if __name__ == "__main__":
    pass
