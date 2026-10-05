"""Posts NASA's Astronomy Picture of the Day as NASA_APOD (module/apod.py).

    python scripts/apod.py            post today's picture unless it is already posted
    python scripts/apod.py --dry-run  print the post without creating it
    python scripts/apod.py --replace  delete the bot's post for today and post it again
    python scripts/apod.py --date 2026-10-05 [...]  another day instead of today

Runs inside the app container from motivetag-apod.timer (twice a day: APOD changes
around midnight US Eastern, and a second run catches a late update), and from the
"APOD post" GitHub Actions workflow.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api import create_app  # noqa: E402
from module import apod  # noqa: E402


def main():
    args = sys.argv[1:]
    date = args[args.index("--date") + 1] if "--date" in args else None
    if date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        sys.exit("--date must look like 2026-10-05")
    entry = apod.fetch(date)
    if entry is None:
        print(f"no APOD page for {date or apod.apod_today()} yet")
        return
    if "--dry-run" in args:
        print(apod.compose(entry))
        print(f"\nmedia: {entry['media_type']} {entry['url']}")
        print(f"copyright: {'yes, no picture copied' if entry['copyright'] else 'no'}")
        return
    app = create_app(os.getenv("FLASK_CONFIG", "pro"))
    with app.app_context():
        result = apod.post_today(entry, replace="--replace" in args)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
