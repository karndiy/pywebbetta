﻿from dotenv import load_dotenv

load_dotenv()

from betta import create_app  # noqa: E402

app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
