"""Posts NASA's Astronomy Picture of the Day as NASA_APOD (module/apod.py).

    python scripts/apod.py            post today's picture unless it is already posted
    python scripts/apod.py --dry-run  print the post without creating it

Runs inside the app container from motivetag-apod.timer (twice a day: APOD changes
around midnight US Eastern, and a second run catches a late update), and from the
"APOD post" GitHub Actions workflow.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import create_app  # noqa: E402
from module import apod  # noqa: E402


def main():
    entry = apod.fetch()
    if "--dry-run" in sys.argv:
        print(apod.compose(entry))
        print(f"\nmedia: {entry.get('media_type')} {entry.get('url')}")
        print(f"copyright: {entry.get('copyright') or 'none (public domain)'}")
        return
    app = create_app(os.getenv("FLASK_CONFIG", "pro"))
    with app.app_context():
        print(json.dumps(apod.post_today(entry), ensure_ascii=False))


if __name__ == "__main__":
    main()
