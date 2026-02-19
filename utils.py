import os
import glob
import re
# import sys
import subprocess
from pathlib import Path
import logging

from typing import Tuple, Sequence, Union, List


PathLike = Union[str, Path]


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

# def get_title_from_LaTeX_project(directory: str) -> str:
#     main_file = "main.tex"
#     if os.path.isfile(os.path.join(directory, main_file)):
#         title_line = extract_title_from_TeX_file(
#             os.path.join(directory, main_file)
#         )
#     else:
#         for filepath in glob.glob(os.path.join(directory, "*.tex")):
#             title_line = extract_title_from_TeX_file(filepath)
#             if title_line != "":
#                 break
#     title = get_title_from_LaTeX_line(title_line)
#     return title

def get_title_from_LaTeX_project(
    directory: PathLike,
    *,
    main_file: str = "main.tex",
) -> str:
    """
    Extract the LaTeX document title from a project directory.

    The function looks for a `\title{...}` command. It prioritizes `main.tex`
    if present, otherwise it scans all `*.tex` files in the directory and
    returns the first title found.

    Args:
        directory: Project directory containing LaTeX sources.
        main_file: Preferred entrypoint filename (default: "main.tex").

    Returns:
        The raw LaTeX title string (contents inside `\title{...}`), or an empty
        string if no title command is found.

    Raises:
        NotADirectoryError: If `directory` is not an existing directory.
    """
    dirpath = Path(directory)

    if not dirpath.is_dir():
        raise NotADirectoryError(f"Not a directory: {dirpath}")

    main_path = dirpath / main_file
    if main_path.is_file():
        title_cmd = extract_title_from_TeX_file(main_path)
        return get_title_from_LaTeX_command(title_cmd)

    # Fall back: scan .tex files (stable ordering for determinism)
    for tex_path in sorted(dirpath.glob("*.tex")):
        title_cmd = extract_title_from_TeX_file(tex_path)
        if title_cmd:
            return get_title_from_LaTeX_command(title_cmd)

    return ""

# def extract_title_from_TeX_file(filepath: str) -> str:
#     file_contents = ''
#     with open(filepath, 'r') as file:
#         for line in file:
#             comment_char_idxs = character_idxs(line, '%')
#             entire_line_is_commented = False
#             comment_start = -1

#             for idx in comment_char_idxs:
#                 if idx == 0:
#                     # Entire line is commented out
#                     entire_line_is_commented = True
#                     break
#                 elif line[idx-1] == '\\':
#                     # This comment characted is escaped
#                     continue
#                 else:
#                     # This is where the comment on this line begins
#                     comment_start = idx
#                     break

#             if entire_line_is_commented: continue
#             file_contents += line[0:comment_start].strip()
    
#     title_location = file_contents.find("\\title")
#     if title_location == -1:
#         return ''
#     else:
#         return extract_first_latex_command(file_contents[title_location:])

def extract_title_from_TeX_file(filepath: PathLike) -> str:
    """
    Extract the first `\title{...}` command from a TeX file, ignoring comments.

    This is a heuristic parser:
    - Removes LaTeX comments starting with an unescaped `%`.
    - Concatenates the uncommented content.
    - Locates the first occurrence of `\title` and returns the full command
      substring, e.g. `\title{My Title}` (including braces).

    Args:
        filepath: Path to a `.tex` file.

    Returns:
        The first `\title{...}` command substring, or an empty string if none
        is found.

    Raises:
        FileNotFoundError: If `filepath` does not exist.
        IsADirectoryError: If `filepath` is a directory.
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
    """
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f"TeX file not found: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"Expected a file, got directory: {path}")

    # Build a comment-stripped buffer to search through.
    # Note: We keep some whitespace (a single space) to avoid accidental
    # token concatenation like "...}{..." becoming "...}{...".
    buf_parts: List[str] = []
    with path.open("r", encoding="utf-8") as f:
        for raw_line in f:
            line = strip_latex_comment(raw_line)
            if line:
                buf_parts.append(line.strip())

    buf = " ".join(buf_parts)
    loc = buf.find(r"\title")
    if loc < 0:
        return ""

    return extract_first_latex_command(buf[loc:])

# def extract_first_latex_command(string: str):
#     count_opening_curly = 0
#     count_closing_curly = 0

#     i = 0

#     while True:
#         if string[i] == '{':
#             if i != 0 and string[i-1] == '\\':
#                 # This opening curly bracket is escaped
#                 pass
#             else:
#                 # We have an opening curly bracket
#                 count_opening_curly += 1
#         else:
#             pass

#         if string[i] == '}':
#             if i == 0:
#                 # String starts with closing curly bracket
#                 raise ValueError
#             elif string[i-1] == '\\':
#                 # This closing curly bracket is escaped
#                 pass
#             else:
#                 # We have a closing curly bracket
#                 count_closing_curly += 1
#         else:
#             pass
        
#         i += 1

#         if count_opening_curly > 0 and count_opening_curly == count_closing_curly:
#             break

#     return string[:i]

def extract_first_latex_command(text: str) -> str:
    """
    Extract a LaTeX command that starts at the beginning of `text` and ends at
    the matching closing brace of its first brace group.

    Example:
        input:  "\title{A {nested} title} some more"
        output: "\title{A {nested} title}"

    This function assumes the LaTeX command uses brace arguments and returns up
    to and including the matching `}` for the first encountered unescaped `{`.

    Args:
        text: String starting with a LaTeX command (e.g. "\\title{...}").

    Returns:
        Substring containing the command and its first complete brace group.

    Raises:
        ValueError: If no opening brace is found or braces do not balance.
    """
    if not text:
        raise ValueError("Empty input to extract_first_latex_command()")

    start = text.find("{")
    if start < 0:
        raise ValueError("No '{' found in LaTeX command")

    depth = 0
    i = 0
    n = len(text)

    while i < n:
        c = text[i]

        if c == "{":
            if i > 0 and text[i - 1] == "\\":
                # escaped \{
                pass
            else:
                depth += 1

        elif c == "}":
            if i > 0 and text[i - 1] == "\\":
                # escaped \}
                pass
            else:
                depth -= 1
                if depth == 0:
                    # include this closing brace
                    return text[: i + 1]

        i += 1

    raise ValueError("Unbalanced braces in LaTeX command")

def character_idxs(string: str, match: str) -> List[int]:
    """
    Return all indices where `match` occurs in `string`.

    Args:
        string: Input string to scan.
        match: Single-character substring to match.

    Returns:
        List of integer indices where `string[idx] == match`.

    Raises:
        ValueError: If `match` is not a single character.
    """
    if len(match) != 1:
        raise ValueError("`match` must be a single character")
    return [idx for idx, c in enumerate(string) if c == match]

def get_title_from_LaTeX_command(command: str) -> str:
    """
    Extract the title contents from a `\\title{...}` command substring.

    Args:
        command: A substring like "\\title{My Title}". May include whitespace.

    Returns:
        The contents inside the outermost braces, e.g. "My Title".
        Returns an empty string if `command` is empty.

    Raises:
        ValueError: If `command` is non-empty but does not contain a brace group.
    """
    if not command:
        return ""

    # Be tolerant: allow leading whitespace/newlines
    s = command.strip()

    # Find the first brace group and return its contents.
    lb = s.find("{")
    rb = s.rfind("}")
    if lb < 0 or rb < 0 or rb <= lb:
        raise ValueError(f"Malformed title command: {command!r}")

    return s[lb + 1 : rb]

def strip_latex_comment(line: str) -> str:
    """
    Strip the LaTeX comment portion from a single line.

    A LaTeX comment begins at the first `%` that is not escaped by a preceding
    backslash. If the first non-escaped `%` occurs at column 0, the entire line
    is considered a comment and returns "".

    Args:
        line: One line of TeX source (including its trailing newline).

    Returns:
        The portion of `line` before the comment, or "" if the line is entirely
        commented.
    """
    # Fast path: no percent at all.
    if "%" not in line:
        return line

    for i, c in enumerate(line):
        if c != "%":
            continue
        if i == 0:
            return ""
        if line[i - 1] == "\\":
            # Escaped percent \% => not a comment start
            continue
        return line[:i]

    return line

def hyphenate_string(string: str) -> str:
    """
    Convert a string into a hyphen-separated form.

    This function normalizes whitespace and replaces runs of whitespace
    characters with a single hyphen (`-`). Leading and trailing whitespace
    is removed before conversion.

    Examples:
        "My Paper Title"      -> "My-Paper-Title"
        "  A   B   C  "       -> "A-B-C"
        "Title\\twith\\nspace" -> "Title-with-space"

    Args:
        string: Input string.

    Returns:
        A hyphen-separated version of the input string.
    """
    if not string:
        return ""

    # Normalize all whitespace (spaces, tabs, newlines) to a single space
    normalized = re.compile(r"\s+").sub(" ", string.strip())

    # Replace spaces with hyphens
    return normalized.replace(" ", "-")

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
