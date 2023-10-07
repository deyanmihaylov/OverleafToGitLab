def get_Overleaf_url_from_hash(hash_slug: str) -> str:
    url = f"https://git.overleaf.com/{hash_slug}"
    return url

def get_hash_from_Overleaf_url(url: str) -> str:
    hash_slug = url.rsplit('/', 1)[-1]
    return hash_slug

if __name__ == "__main__":
    pass
    