import os
import sqlite3
import sys
import unicodedata
from contextlib import closing
from datetime import date, datetime
from pathlib import Path

# Project directory location.
BASE_DIR = Path(__file__).resolve().parent

# Keep development data separate from executable data.
if getattr(sys, "frozen", False):
    local_app_data = os.environ.get("LOCALAPPDATA")

    if local_app_data:
        DATA_DIR = Path(local_app_data) / "POS-Bar"
    else:
        DATA_DIR = Path.home() / "AppDate" / "Local" / "POS-Bar"

else:
    DATA_DIR = BASE_DIR / "data"


# Permanent data paths.
DB_PATH = DATA_DIR / "pos.sqlite3"
BACKUP_DIR = DATA_DIR / "backups"


def normalize_product_name(name):
    """Normalises product names to detect duplicates."""

    normalized = unicodedata.normalize("NFD", name.casefold())

    normalized = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )

    # Remove repeated and leading/trailing whitespace.
    normalized = " ".join(normalized.split())

    return normalized

def get_connection():
    """Creates a connection to the SQLite database."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    # Enable foreign key enforcement.
    connection.execute("PRAGMA foreign_keys = ON")

    return connection

def get_admin_lockout_state():
    """Gets the number of failed attempts and the lockout expiry time."""

    with closing(get_connection()) as connection:
        rows = connection.execute(
            """
            SELECT setting_key, setting_value
            FROM settings
            WHERE setting_key IN (
                'admin_failed_attempts',
                'admin_locked_until'
            )
            """
        ).fetchall()

    settings = dict(rows)

    try:
        failed_attempts = int(
            settings.get("admin_failed_attempts", "0")
        )
    except (TypeError, ValueError):
        failed_attempts = 0

    locked_until = settings.get("admin_locked_until", "")

    return failed_attempts, locked_until

def save_admin_lockout_state(failed_attempts, locked_until=""):
    """Saves the administration access attempt state."""

    settings = {
        "admin_failed_attempts": str(failed_attempts),
        "admin_locked_until": locked_until,
    }

    with closing(get_connection()) as connection:
        for key, value in settings.items():
            connection.execute(
                """
                INSERT OR REPLACE INTO settings (
                    setting_key,
                    setting_value
                )
                VALUES (?, ?)
                """,
                (key, value),
            )

        connection.commit()

def initialize_database():
    """Creates the tables and the 12 product slots."""

    with closing(get_connection()) as connection:

        connection.executescript("""


        CREATE TABLE IF NOT EXISTS products (
            slot INTEGER PRIMARY KEY CHECK (slot BETWEEN 1 AND 12),

            name TEXT,
            name_normalized TEXT,
            price_cents INTEGER,

            CHECK (
                (name IS NULL AND name_normalized IS NULL AND price_cents IS NULL)
                OR
                (
                    name IS NOT NULL
                    AND length(trim(name)) > 0
                    AND name_normalized IS NOT NULL
                    AND length(trim(name_normalized)) > 0
                    AND price_cents IS NOT NULL
                    AND price_cents >= 0
                )
            ),

            UNIQUE (name_normalized)
        );



            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL
                    DEFAULT (datetime('now', 'localtime')),
                total_cents INTEGER NOT NULL
                    CHECK (total_cents >= 0)
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                sale_id INTEGER NOT NULL,
                product_slot INTEGER NOT NULL,

                product_name TEXT NOT NULL
                    CHECK (length(trim(product_name)) > 0),

                unit_price_cents INTEGER NOT NULL
                    CHECK (
                        typeof(unit_price_cents) = 'integer'
                        AND unit_price_cents >= 0
                    ),

                quantity INTEGER NOT NULL
                    CHECK (
                        typeof(quantity) = 'integer'
                        AND quantity > 0
                    ),

                FOREIGN KEY (sale_id)
                    REFERENCES sales(id) ON DELETE CASCADE,

                FOREIGN KEY (product_slot)
                    REFERENCES products(slot)
            );

            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            );


            CREATE INDEX IF NOT EXISTS idx_sales_created_at
            ON sales(created_at);


            CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id
            ON sale_items(sale_id);

        """)

        # Create the 9 default products
        for slot in range(1, 10):
            name = f"Product {slot}"

            connection.execute(
                """
                INSERT OR IGNORE INTO products
                (slot, name, name_normalized, price_cents)
                VALUES (?, ?, ?, ?)
                """,
                (slot, name, normalize_product_name(name), 0)
            )

        # Reserve the 3 additional slots
        for slot in range(10, 13):
            connection.execute(
                """
                INSERT OR IGNORE INTO products
                (slot, name, price_cents)
                VALUES (?, NULL, NULL)
                """,
                (slot,)
            )

        connection.commit()

def list_products():
    """Returns all product slots."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT slot, name, price_cents
            FROM products
            ORDER BY slot
            """
        ).fetchall()

def update_products(products):
    """Updates multiple products in a single operation."""

    with closing(get_connection()) as connection:
        try:
            for slot, name, price_cents in products:
                if name is None:
                    normalized_name = None
                else:
                    normalized_name = normalize_product_name(name)

                connection.execute(
                    """
                    UPDATE products
                    SET name = ?,
                        name_normalized = ?,
                        price_cents = ?
                    WHERE slot = ?
                    """,
                    (name, normalized_name, price_cents, slot)
                )

            connection.commit()

        except Exception:
            connection.rollback()
            raise

def save_sale(cart):
    """Saves a sale and its items."""

    if not cart:
        raise ValueError("The cart is empty.")

    with closing(get_connection()) as connection:

        try:
            # Calculate the total
            total_cents = sum(
                product["price_cents"] * product["quantity"]
                for product in cart.values()
            )

            # Record the sale
            cursor = connection.execute(
                """
                INSERT INTO sales (total_cents)
                VALUES (?)
                """,
                (total_cents,)
            )

            sale_id = cursor.lastrowid

            # Record the sale items
            for slot, product in cart.items():

                connection.execute(
                    """
                    INSERT INTO sale_items (
                        sale_id,
                        product_slot,
                        product_name,
                        unit_price_cents,
                        quantity
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        slot,
                        product["name"],
                        product["price_cents"],
                        product["quantity"]
                    )
                )

            connection.commit()

            return sale_id, total_cents

        except Exception:
            connection.rollback()
            raise

def list_sales():
    """Returns all sales, from newest to oldest."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT id, created_at, total_cents
            FROM sales
            ORDER BY id DESC
            """
        ).fetchall()

def get_sale_details(sale_id):
    """Returns a sale and its items."""

    with closing(get_connection()) as connection:

        sale = connection.execute(
            """
            SELECT id, created_at, total_cents
            FROM sales
            WHERE id = ?
            """,
            (sale_id,)
        ).fetchone()

        if sale is None:
            return None

        items = connection.execute(
            """
            SELECT
                product_name,
                unit_price_cents,
                quantity,
                unit_price_cents * quantity AS subtotal_cents
            FROM sale_items
            WHERE sale_id = ?
            ORDER BY id
            """,
            (sale_id,)
        ).fetchall()

        return sale, items

def get_daily_sales_summary():
    """Returns the number of sales and total revenue grouped by day."""

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT
                DATE(created_at) AS sale_date,
                COUNT(*) AS sales_count,
                SUM(total_cents) AS total_cents
            FROM sales
            GROUP BY DATE(created_at)
            ORDER BY sale_date DESC
            """
        ).fetchall()

def export_sales_data(start_date=None, end_date=None):
    """Returns sales and items within the specified period.

    Dates must use the YYYY-MM-DD format.
    The start and end dates are inclusive.
    If no dates are provided, all sales are returned.
    """

    conditions = []
    parameters = []

    if start_date:
        conditions.append("DATE(s.created_at) >= DATE(?)")
        parameters.append(start_date)

    if end_date:
        conditions.append("DATE(s.created_at) <= DATE(?)")
        parameters.append(end_date)

    query = """
        SELECT
            s.id AS sale_id,
            s.created_at,
            s.total_cents,
            si.product_name,
            si.quantity,
            si.unit_price_cents,
            si.unit_price_cents * si.quantity AS subtotal_cents
        FROM sales AS s
        INNER JOIN sale_items AS si
            ON si.sale_id = s.id
    """

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY s.id ASC, si.id ASC"

    with closing(get_connection()) as connection:
        return connection.execute(query, parameters).fetchall()

def create_database_backup():
    """Creates or updates the daily backup and removes older backups."""

    backup_dir = BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_dir / (
        f"pos_backup_{date.today().isoformat()}.sqlite3"
    )

    temp_path = backup_path.with_suffix(".tmp")

    try:
        with closing(get_connection()) as source, closing(
            sqlite3.connect(temp_path)
        ) as destination:
            source.backup(destination)

        # Replaces the previous backup only after the new one is complete.
        temp_path.replace(backup_path)

    finally:
        if temp_path.exists():
            temp_path.unlink()

    cleanup_old_database_backups()

    return backup_path

def restore_database_backup(backup_path):
    """Restores a backup after validating the file.

    Before replacing the current database, creates an additional backup
    so the previous state can be recovered.
    """

    backup_path = Path(backup_path).resolve()

    if not backup_path.is_file():
        raise FileNotFoundError(
            "The backup file could not be found."
        )

    with closing(sqlite3.connect(backup_path)) as source:

        # Check the integrity of the selected backup
        integrity = source.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if integrity is None or integrity[0] != "ok":
            raise sqlite3.DatabaseError(
                "The backup is corrupted."
            )

        # Confirm that it contains the tables required by the POS
        tables = {
            row[0]
            for row in source.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        required_tables = {
            "products",
            "sales",
            "sale_items",
            "settings"
        }

        missing_tables = required_tables - tables

        if missing_tables:
            raise sqlite3.DatabaseError(
                "The selected file does not contain all "
                "tables required by the POS."
            )

        # Create a backup of the current state
        backup_dir = BACKUP_DIR
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        safety_path = backup_dir / (
            f"pos_antes_restauro_{timestamp}.sqlite3"
        )

        with closing(get_connection()) as current, closing(
            sqlite3.connect(safety_path)
        ) as safety:
            current.backup(safety)

        # Restore the selected backup
        with closing(get_connection()) as destination:
            source.backup(destination)

    return safety_path

def cleanup_old_database_backups(keep=30, backup_dir=None):
    """Keeps only the most recent daily backups."""

    if backup_dir is None:
        backup_dir = BACKUP_DIR
    else:
        backup_dir = Path(backup_dir)

    if not backup_dir.exists():
        return

    daily_backups = sorted(
        backup_dir.glob("pos_backup_????-??-??.sqlite3"),
        reverse=True,
    )

    for old_backup in daily_backups[keep:]:
        old_backup.unlink()
