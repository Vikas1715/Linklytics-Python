"""
url_service.py
---------------
Handles generating a unique short code for a URL.

Approach: Base62 random string.
- Base62 alphabet = a-z, A-Z, 0-9 (62 characters total). It's called
  "Base62" because it uses 62 possible symbols per character.
- These characters are all URL-safe (no need to escape them in a link).
- We pick a code length that gives us plenty of unique combinations:
  62^7 is over 3.5 trillion possibilities, more than enough for this project.

Collision handling: it's astronomically unlikely two random codes collide,
but we still check the database and retry a few times, just to be correct.
"""

import random
import string

BASE62_ALPHABET = string.ascii_letters + string.digits  # a-zA-Z0-9
SHORT_CODE_LENGTH = 7
MAX_GENERATION_ATTEMPTS = 5


def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    """Generates a random Base62 string of the given length."""
    return "".join(random.choices(BASE62_ALPHABET, k=length))


def generate_unique_short_code(db_session, url_model) -> str:
    """
    Generates a short code and checks the database to make sure it doesn't
    already exist. Retries a few times in the (very unlikely) event of a
    collision, then gives up with an error - this keeps the logic simple
    and easy to explain instead of building a complex ID-generation system.
    """
    for _ in range(MAX_GENERATION_ATTEMPTS):
        code = generate_short_code()
        exists = db_session.query(url_model).filter(url_model.short_code == code).first()
        if not exists:
            return code

    raise RuntimeError("Could not generate a unique short code, please try again.")
