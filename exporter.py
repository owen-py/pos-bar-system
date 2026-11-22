import csv


def format_euros(cents):
    """Converts cents to euros using a decimal point."""
    return f"{cents // 100}.{cents % 100:02d}"


def save_sales_csv(sales_data, file_path):
    """Saves sales data to an Excel-compatible CSV file."""

    with open(
        file_path,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as csv_file:

        writer = csv.writer(csv_file, delimiter=";")

        writer.writerow([
            "Sale number",
            "Date and time",
            "Product",
            "Quantity",
            "Unit price (€)",
            "Subtotal (€)",
            "Sale total (€)"
        ])

        previous_sale_id = None

        for item in sales_data:
            sale_id = item["sale_id"]

            # The sale total appears only on the first row of
            # each sale to avoid duplicate values in Excel calculations.
            sale_total = ""

            if sale_id != previous_sale_id:
                sale_total = format_euros(item["total_cents"])

            writer.writerow([
                sale_id,
                item["created_at"],
                item["product_name"],
                item["quantity"],
                format_euros(item["unit_price_cents"]),
                format_euros(item["subtotal_cents"]),
                sale_total
            ])

            previous_sale_id = sale_id
