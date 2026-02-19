# OverleafToGitLab

A small automation tool that converts an Overleaf project into a fully-configured GitLab repository with CI/CD and GitLab Pages support.

The goal is to make academic writing workflows reproducible and version-controlled outside Overleaf while preserving a simple “clone → build → publish PDF” pipeline.

## Overview

`OverleafToGitLab` automates the process of:

 1. Cloning an Overleaf project via its Git interface.
 2. Extracting metadata (e.g. project title) from the LaTeX sources.
 3. Creating a new GitLab repository via the GitLab API.
 4. Linking the cloned project to the new GitLab remote.
 5. Adding a ready-to-use `.gitlab-ci.yml` pipeline.
 6. Enabling automatic PDF builds and GitLab Pages hosting.

After running the script, your Overleaf project becomes a normal GitLab project with CI builds and a Pages URL pointing to the compiled PDF.

## Features

- Automatic Overleaf → GitLab repository migration
- GitLab project creation via API
- Automatic remote configuration and push
- LaTeX CI pipeline (using ``latexmk``)
- GitLab Pages deployment of compiled PDFs
- Title extraction from LaTeX source to generate clean repo names

## Requirements

- Python ≥ 3.9
- Git installed and configured
- Overleaf project with Git access enabled
- GitLab Personal Access Token

Dependencies:

- `GitPython`
- `python-gitlab`

Install:

```bash
pip install -r requirements.txt
```

## Usage

Basic example:

```bash
python sync.py <OVERLEAF_GIT_URL>
```

The script will:

- clone the project locally,
- create a GitLab repository,
- configure remotes,
- push sources,
- install a CI pipeline.

## Configuration

Authentication is done via a GitLab Personal Access Token.

Setthe environment variable:

```bash
export GITLAB_OVERLEAF=<your_token>
```

Alternatively, the script can prompt for a token interactively.

## Output

After a successful run:

- A new GitLab repository is created with the name of the project.
- The LaTeX project is pushed to this GitLab repository.
- CI builds produce a PDF automatically.
- The PDF is available via GitLab Pages.

## License

MIT License
