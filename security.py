import hashlib
import hmac
import secrets

from database import get_connection

# Temporary PIN used only during initial setup
DEFAULT_PIN = "482731"

# Number of iterations used to protect the PIN
PBKDF2_ITERATIONS = 310_000


def _get_setting(key):
    with get_connection() as connection:
        result = connection.execute(
            """
            SELECT setting_value
            FROM settings
            WHERE setting_key = ?
            """,
            (key,)
        ).fetchone()

    return result[0] if result else None


def _save_settings(settings):
    """Saves multiple values in the settings table."""
    connection = get_connection()

    try:
        connection.executemany(
            """
            INSERT INTO settings (setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
            """,
            list(settings.items())
        )

        connection.commit()

    finally:
        connection.close()


def _save_pin(pin, must_change):
    """Stores the PIN using a hash and salt."""
    salt = secrets.token_hex(16)

    pin_hash = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    ).hex()

    _save_settings({
        "admin_pin_salt": salt,
        "admin_pin_hash": pin_hash,
        "admin_pin_must_change": "1" if must_change else "0"
    })


def initialize_security():
    """Creates the initial PIN if one does not already exist in the database."""
    pin_hash = _get_setting("admin_pin_hash")
    salt = _get_setting("admin_pin_salt")

    if not pin_hash or not salt:
        _save_pin(DEFAULT_PIN, must_change=True)


def verify_pin(pin):
    """Checks whether the entered PIN is correct."""
    if not isinstance(pin, str):
        return False

    stored_hash = _get_setting("admin_pin_hash")
    salt = _get_setting("admin_pin_salt")

    if not stored_hash or not salt:
        return False

    calculated_hash = hashlib.pbkdf2_hmac(
        "sha256",
        pin.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    ).hex()

    return hmac.compare_digest(calculated_hash, stored_hash)


def pin_requires_change():
    """Indicates whether the user must change the PIN."""
    return _get_setting("admin_pin_must_change") == "1"


def change_pin(new_pin):
    """Changes the PIN and clears the initial change requirement."""
    valid_pin = (
        isinstance(new_pin, str)
        and len(new_pin) == 6
        and new_pin.isascii()
        and new_pin.isdigit()
    )

    if not valid_pin:
        raise ValueError("The PIN must contain exactly 6 digits.")

    _save_pin(new_pin, must_change=False)
