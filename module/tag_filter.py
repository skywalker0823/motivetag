import re

# A tag is # followed by letters (any language), digits or _. Punctuation ends it:
# Chinese has no spaces, so "#咖啡，很好喝" must give 咖啡, not 咖啡，很好喝.
TAG = re.compile(r"#(\w{1,30})")


def filter(data):
    """The distinct tags in `data`, in the order they first appear."""
    return list(dict.fromkeys(TAG.findall(data or "")))
