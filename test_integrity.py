import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import database


def test_rejection(name, operation):
    """Confirms that the database rejects invalid data."""

    try:
        operation()

    except sqlite3.IntegrityError:
        print(f"PASSED  | {name}")
        return True

    except sqlite3.Error as error:
        print(f"ERROR   | {name}: {error}")
        return False

    print(f"FAILED  | {name}: invalid data was accepted.")
    return False


def run_tests():
    results = []

    # Create a temporary database.
    with tempfile.TemporaryDirectory() as temporary_directory:

        original_data_dir = database.DATA_DIR
        original_db_path = database.DB_PATH

        try:
            test_dir = Path(temporary_directory)

            database.DATA_DIR = test_dir
            database.DB_PATH = test_dir / "test.sqlite3"

            # Create the tables using the current project constraints.
            database.initialize_database()

            # Create a valid sale for the tests.
            with closing(database.get_connection()) as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO sales (total_cents)
                    VALUES (100)
                    """
                )
                sale_id = cursor.lastrowid

                if sale_id is None:
                    raise RuntimeError("Could not retrieve the test sale ID.")

                # Confirm that a valid item is accepted.
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
                    (sale_id, 1, "Test product", 100, 1)
                )

                connection.commit()

            print("\n--- SQLITE INTEGRITY TESTS ---\n")

            def insert_item(
                sale_id: int = sale_id,
                product_slot: int = 1,
                name: str = "Test product",
                price: float = 100,
                quantity: float = 1
            ):
                with closing(database.get_connection()) as connection:
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
                            product_slot,
                            name,
                            price,
                            quantity
                        )
                    )
                    connection.commit()

            def insert_sale(total):
                with closing(database.get_connection()) as connection:
                    connection.execute(
                        """
                        INSERT INTO sales (total_cents)
                        VALUES (?)
                        """,
                        (total,)
                    )
                    connection.commit()

            def alterar_price_produto():
                with closing(database.get_connection()) as connection:
                    connection.execute(
                        """
                        UPDATE products
                        SET price_cents = -1
                        WHERE slot = 1
                        """
                    )
                    connection.commit()

            # 1. Zero quantity.
            results.append(
                test_rejection(
                    "Zero quantity",
                    lambda: insert_item(quantity=0)
                )
            )

            # 2. Negative quantity.
            results.append(
                test_rejection(
                    "Negative quantity",
                    lambda: insert_item(quantity=-1)
                )
            )

            # 3. Quantity decimal.
            results.append(
                test_rejection(
                    "Decimal quantity (1.5)",
                    lambda: insert_item(quantity=1.5)
                )
            )

            # 4. Negative unit price.
            results.append(
                test_rejection(
                    "Negative unit price",
                    lambda: insert_item(price=-1)
                )
            )

            # 5. Price decimal.
            results.append(
                test_rejection(
                    "Decimal unit price",
                    lambda: insert_item(price=1.5)
                )
            )

            # 6. Empty product name.
            results.append(
                test_rejection(
                    "Empty product name",
                    lambda: insert_item(name="")
                )
            )

            # 7. Non-existent sale.
            results.append(
                test_rejection(
                    "Reference to non-existent sale",
                    lambda: insert_item(sale_id=999999)
                )
            )

            # 8. Product inexistente.
            results.append(
                test_rejection(
                    "Reference to non-existent product",
                    lambda: insert_item(product_slot=999)
                )
            )

            # 9. Negative sale total.
            results.append(
                test_rejection(
                    "Negative sale total",
                    lambda: insert_sale(-100)
                )
            )

            # 10. Negative price in products table.
            results.append(
                test_rejection(
                    "Negative price in products table",
                    alterar_price_produto
                )
            )

            print("\n--- FINAL RESULTS ---")

            aprovados = sum(results)
            total = len(results)

            print(f"Tests passed: {aprovados}/{total}")

            if aprovados == total:
                print("\nSUCCESS: All constraints were enforced!")
            else:
                print("\nWARNING: Some constraints need to be checked.")

        finally:
            # Restore the application paths.
            database.DATA_DIR = original_data_dir
            database.DB_PATH = original_db_path


if __name__ == "__main__":
    run_tests()
