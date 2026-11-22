import sqlite3
import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import ttk

from admin import AdminWindow
from database import (
    create_database_backup,
    initialize_database,
    list_products,
    save_sale,
    update_products,
)
from security import initialize_security
from window_utils import center_window


def format_money(cents):
    """Converts cents to a euro amount."""

    euros, remaining_cents = divmod(cents, 100)
    euros_formatted = f"{euros:,}"

    return f"€{euros_formatted}.{remaining_cents:02d}"


class POSApp:

    def __init__(self):

        initialize_database()
        initialize_security()

        # Cart: stores the selected products
        self.cart = {}

        # Sale total in cents
        self.total_cents = 0

        self.product_buttons = {}

        # Main window
        self.root = tk.Tk()
        self.root.title("POS - Bar / Restaurante")
        center_window(self.root, 1100, 700)
        self.root.minsize(900, 600)

        self.configure_styles()
        self.create_interface()
        self.create_backup()

    def configure_styles(self):
        """Configures the application theme."""

        style = ttk.Style(self.root)

        if "clam" in style.theme_names():
            style.theme_use("clam")

        # Colour palette
        background = "#F2F5F7"
        panel = "#FFFFFF"
        navy = "#183B4E"
        teal = "#168477"
        teal_dark = "#116C62"
        green = "#21865B"
        green_dark = "#196B48"
        red = "#C94C4C"
        red_dark = "#A83B3B"
        text = "#253746"
        border = "#D7E0E5"
        selected = "#DCEFEB"

        # Main background
        self.root.configure(bg=background)

        # Fonte e estilos gerais
        style.configure(
            ".",
            font=("Segoe UI", 10),
            foreground=text
        )

        style.configure(
            "TFrame",
            background=background
        )

        style.configure(
            "TLabel",
            background=background,
            foreground=text,
            font=("Segoe UI", 10)
        )


        # Panels and configuration areas
        style.configure(
            "TLabelframe",
            background=background,
            bordercolor=border,
            relief="solid",
            borderwidth=1
        )

        style.configure(
            "TLabelframe.Label",
            background=background,
            foreground=navy,
            font=("Segoe UI", 10, "bold")
        )

        # Table and form headings
        style.configure(
            "TableHeader.TLabel",
            background=background,
            foreground=navy,
            font=("Segoe UI", 10, "bold")
        )

        style.configure(
            "Title.TLabel",
            background=background,
            foreground=navy,
            font=("Segoe UI", 22, "bold")
        )

        style.configure(
            "Section.TLabel",
            background=background,
            foreground=navy,
            font=("Segoe UI", 15, "bold")
        )

        # Standard buttons
        style.configure(
            "TButton",
            font=("Segoe UI", 10, "bold"),
            background=panel,
            foreground=navy,
            padding=(14, 9),
            borderwidth=1,
            bordercolor=border,
            focusthickness=2,
            focuscolor=teal
        )

        style.map(
            "TButton",
            background=[
                ("pressed", teal_dark),
                ("active", "#E2F0ED")
            ],
            foreground=[
                ("pressed", "#FFFFFF"),
                ("active", navy)
            ]
        )

        # Product buttons
        style.configure(
            "Product.TButton",
            font=("Segoe UI", 13, "bold"),
            background=panel,
            foreground=navy,
            padding=(12, 20),
            borderwidth=1,
            bordercolor=border
        )

        style.map(
            "Product.TButton",
            background=[
                ("pressed", teal_dark),
                ("active", selected)
            ],
            foreground=[
                ("pressed", "#FFFFFF"),
                ("active", navy)
            ]
        )

        # Empty slots: keep their position without looking like buttons.
        style.configure(
            "Empty.Product.TButton",
            background=background,
            foreground=background,
            padding=(12, 20),
            borderwidth=0,
            relief="flat",
            focusthickness=0,
            focuscolor=background
        )

        style.map(
            "Empty.Product.TButton",
            background=[
                ("disabled", background),
                ("active", background),
                ("pressed", background)
            ],
            foreground=[
                ("disabled", background),
                ("active", background),
                ("pressed", background)
            ]
        )

        # Button used to complete a sale
        style.configure(
            "Success.TButton",
            font=("Segoe UI", 11, "bold"),
            background=green,
            foreground="#FFFFFF",
            padding=(14, 9),
            borderwidth=0
        )

        style.map(
            "Success.TButton",
            background=[
                ("pressed", green_dark),
                ("active", green_dark)
            ],
            foreground=[
                ("disabled", "#DCE8E1")
            ]
        )

        # Buttons used for removal actions
        style.configure(
            "Danger.TButton",
            font=("Segoe UI", 10, "bold"),
            background=red,
            foreground="#FFFFFF",
            padding=(12, 9),
            borderwidth=0
        )

        style.map(
            "Danger.TButton",
            background=[
                ("pressed", red_dark),
                ("active", red_dark)
            ]
        )

        # Sale total
        style.configure(
            "Total.TLabel",
            background=background,
            foreground=navy,
            font=("Segoe UI", 24, "bold")
        )

        # Tables
        style.configure(
            "Treeview",
            font=("Segoe UI", 10),
            background=panel,
            fieldbackground=panel,
            foreground=text,
            rowheight=34,
            borderwidth=0
        )

        style.configure(
            "Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            background="#E7EEF2",
            foreground=navy,
            padding=(8, 10),
            relief="flat"
        )

        style.map(
            "Treeview",
            background=[
                ("selected", selected)
            ],
            foreground=[
                ("selected", navy)
            ]
        )

        # Text input fields
        style.configure(
            "TEntry",
            font=("Segoe UI", 10),
            fieldbackground=panel,
            foreground=text,
            padding=7
        )

        # Checkboxes
        style.configure(
            "TCheckbutton",
            font=("Segoe UI", 10),
            background=background,
            foreground=text
        )

        style.configure(
            "TRadiobutton",
            font=("Segoe UI", 10),
            background=background,
            foreground=text
        )

    def show_success_dialog(self, title, message, parent=None):
        """Displays a success message using the application theme."""

        background = "#F2F5F7"
        navy = "#183B4E"
        green = "#21865B"

        if parent is None:
            parent = self.root

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        style = ttk.Style(dialog)
        style.configure(
            "POSSuccessDialog.TFrame",
            background=background
        )
        style.configure(
            "POSSuccessDialog.Title.TLabel",
            font=("Segoe UI", 15, "bold"),
            background=background,
            foreground=green
        )
        style.configure(
            "POSSuccessDialog.Message.TLabel",
            font=("Segoe UI", 10),
            background=background,
            foreground=navy
        )

        frame = ttk.Frame(
            dialog,
            style="POSSuccessDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=title,
            style="POSSuccessDialog.Title.TLabel"
        ).grid(row=0, column=0, pady=(5, 15))

        ttk.Label(
            frame,
            text=message,
            style="POSSuccessDialog.Message.TLabel",
            justify="center",
            wraplength=460
        ).grid(row=1, column=0, sticky="n", pady=(0, 10))

        ttk.Button(
            frame,
            text="OK",
            style="TButton",
            command=dialog.destroy,
            width=12
        ).grid(row=2, column=0, sticky="s", pady=(10, 0))

        center_window(dialog, 520, 300)

        dialog.wait_visibility()
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

    def show_error_dialog(self, title, message, parent=None):
        """Displays an error message using the application theme."""

        background = "#F2F5F7"
        navy = "#183B4E"
        red = "#C94C4C"

        if parent is None:
            parent = self.root

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        style = ttk.Style(dialog)
        style.configure(
            "POSErrorDialog.TFrame",
            background=background
        )
        style.configure(
            "POSErrorDialog.Title.TLabel",
            font=("Segoe UI", 15, "bold"),
            background=background,
            foreground=red
        )
        style.configure(
            "POSErrorDialog.Message.TLabel",
            font=("Segoe UI", 10),
            background=background,
            foreground=navy
        )

        frame = ttk.Frame(
            dialog,
            style="POSErrorDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=title,
            style="POSErrorDialog.Title.TLabel"
        ).grid(row=0, column=0, pady=(5, 15))

        ttk.Label(
            frame,
            text=message,
            style="POSErrorDialog.Message.TLabel",
            justify="center",
            wraplength=460
        ).grid(row=1, column=0, sticky="n", pady=(0, 10))

        ttk.Button(
            frame,
            text="OK",
            style="TButton",
            command=dialog.destroy,
            width=12
        ).grid(row=2, column=0, sticky="s", pady=(10, 0))

        center_window(dialog, 520, 300)

        dialog.wait_visibility()
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

    def show_confirm_dialog(self, title, message, total, parent=None):
        """Requests confirmation using the application theme."""

        background = "#F2F5F7"
        navy = "#183B4E"
        green = "#21865B"

        if parent is None:
            parent = self.root

        result = {"confirmed": False}

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        style = ttk.Style(dialog)
        style.configure(
            "POSConfirmDialog.TFrame",
            background=background
        )
        style.configure(
            "POSConfirmDialog.Title.TLabel",
            font=("Segoe UI", 15, "bold"),
            background=background,
            foreground=navy
        )
        style.configure(
            "POSConfirmDialog.Message.TLabel",
            font=("Segoe UI", 10),
            background=background,
            foreground=navy
        )
        style.configure(
            "POSConfirmDialog.Total.TLabel",
            font=("Segoe UI", 22, "bold"),
            background=background,
            foreground=green
        )

        frame = ttk.Frame(
            dialog,
            style="POSConfirmDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=title,
            style="POSConfirmDialog.Title.TLabel"
        ).grid(row=0, column=0, pady=(5, 12))

        ttk.Label(
            frame,
            text=message,
            style="POSConfirmDialog.Message.TLabel",
            justify="center",
            wraplength=400
        ).grid(row=1, column=0, pady=(0, 12))

        ttk.Label(
            frame,
            text=total,
            style="POSConfirmDialog.Total.TLabel"
        ).grid(row=2, column=0, pady=(0, 20))

        buttons_frame = ttk.Frame(
            frame,
            style="POSConfirmDialog.TFrame"
        )
        buttons_frame.grid(row=3, column=0, sticky="ew")

        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)

        def cancel():
            dialog.destroy()

        def confirm():
            result["confirmed"] = True
            dialog.destroy()

        ttk.Button(
            buttons_frame,
            text="Cancel",
            style="TButton",
            command=cancel
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ttk.Button(
            buttons_frame,
            text="Confirm sale",
            style="Success.TButton",
            command=confirm
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.bind("<Escape>", lambda event: cancel())
        dialog.bind("<Return>", lambda event: confirm())

        center_window(dialog, 480, 280)

        dialog.wait_visibility()
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

        return result["confirmed"]

    def show_warning_dialog(self, title, message, parent=None):
        """Displays a warning message using the application theme."""

        background = "#F2F5F7"
        navy = "#183B4E"
        orange = "#C47A16"

        if parent is None:
            parent = self.root

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        style = ttk.Style(dialog)
        style.configure(
            "POSWarningDialog.TFrame",
            background=background
        )
        style.configure(
            "POSWarningDialog.Title.TLabel",
            font=("Segoe UI", 15, "bold"),
            background=background,
            foreground=orange
        )
        style.configure(
            "POSWarningDialog.Message.TLabel",
            font=("Segoe UI", 10),
            background=background,
            foreground=navy
        )

        frame = ttk.Frame(
            dialog,
            style="POSWarningDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=title,
            style="POSWarningDialog.Title.TLabel"
        ).grid(row=0, column=0, pady=(5, 15))

        ttk.Label(
            frame,
            text=message,
            style="POSWarningDialog.Message.TLabel",
            justify="center",
            wraplength=460
        ).grid(row=1, column=0, sticky="n", pady=(0, 10))

        ttk.Button(
            frame,
            text="OK",
            style="TButton",
            command=dialog.destroy,
            width=12
        ).grid(row=2, column=0, sticky="s", pady=(10, 0))

        center_window(dialog, 520, 300)

        dialog.wait_visibility()
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

    def create_interface(self):

        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Button Administration
        admin_button = ttk.Button(
            main_frame,
            text="Administration",
            command=self.open_admin
        )
        admin_button.pack(anchor="e", pady=(10, 0))

        # Main area
        content = ttk.Frame(main_frame)
        content.pack(fill="both", expand=True)

        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        # ---------------------------------
        # PRODUCT AREA
        # ---------------------------------

        products_frame = ttk.LabelFrame(
            content,
            text=" Products ",
            padding=15
        )

        products_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(0, 10)
        )

        for col in range(3):
            products_frame.columnconfigure(col, weight=1)

        for row in range(4):
            products_frame.rowconfigure(row, weight=1)

        products = list_products()

        # Create the 12 buttons
        for product in products:

            slot = product["slot"]
            name = product["name"]
            price = product["price_cents"]

            if name is None:

                button_text = "\n"
                button_style = "Empty.Product.TButton"
                button_state = "disabled"

            else:

                button_text = (
                    f"{name}\n"
                    f"{format_money(price)}"
                )

                button_style = "Product.TButton"
                button_state = "normal"

            button = ttk.Button(
                products_frame,
                text=button_text,
                style=button_style,
                state=button_state,
                command=lambda p=product: self.add_product(p)
            )

            button.grid(
                row=(slot - 1) // 3,
                column=(slot - 1) % 3,
                sticky="nsew",
                padx=5,
                pady=5
            )

            self.product_buttons[slot] = button

        # Button used to manage products
        ttk.Button(
            products_frame,
            text="Manage products and prices",
            command=self.open_product_manager
        ).grid(
            row=4,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=5,
            pady=(12, 0)
        )


        # ---------------------------------
        # SALE AREA
        # ---------------------------------

        sale_frame = ttk.LabelFrame(
            content,
            text=" Current sale ",
            padding=15
        )

        sale_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(10, 0)
        )

        sale_frame.columnconfigure(0, weight=1)
        sale_frame.rowconfigure(1, weight=1)

        ttk.Label(
            sale_frame,
            text="Selected products:",
            style="Section.TLabel"
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 10)
        )

        # Cart table
        tree_frame = ttk.Frame(sale_frame)

        tree_frame.grid(
            row=1,
            column=0,
            sticky="nsew"
        )

        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.cart_tree = ttk.Treeview(
            tree_frame,
            columns=(
                "product",
                "quantity",
                "price",
                "subtotal"
            ),
            show="headings",
            selectmode="browse"
        )

        self.cart_tree.heading(
            "product",
            text="Product"
        )

        self.cart_tree.heading(
            "quantity",
            text="Qty."
        )

        self.cart_tree.heading(
            "price",
            text="Price"
        )

        self.cart_tree.heading(
            "subtotal",
            text="Subtotal"
        )

        self.cart_tree.column(
            "product",
            width=120,
            anchor="w"
        )

        self.cart_tree.column(
            "quantity",
            width=45,
            anchor="center"
        )

        self.cart_tree.column(
            "price",
            width=75,
            anchor="e"
        )

        self.cart_tree.column(
            "subtotal",
            width=85,
            anchor="e"
        )

        self.cart_tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        scrollbar = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.cart_tree.yview
        )

        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.cart_tree.configure(
            yscrollcommand=scrollbar.set
        )

        # Cart control buttons
        controls = ttk.Frame(sale_frame)

        controls.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=10
        )

        ttk.Button(
            controls,
            text="- 1 Qty.",
            command=self.decrease_quantity
        ).pack(side="left", padx=(0, 5))

        ttk.Button(
            controls,
            text="Remove",
            style="Danger.TButton",
            command=self.remove_product
        ).pack(side="left", padx=5)

        ttk.Button(
            controls,
            text="Clear",
            style="Danger.TButton",
            command=self.clear_cart
        ).pack(side="left", padx=5)

        # Separator
        ttk.Separator(
            sale_frame,
            orient="horizontal"
        ).grid(
            row=3,
            column=0,
            sticky="ew",
            pady=10
        )

        ttk.Label(
            sale_frame,
            text="TOTAL"
        ).grid(
            row=4,
            column=0,
            sticky="w"
        )

        self.total_label = ttk.Label(
            sale_frame,
            text="€0.00",
            style="Total.TLabel"
        )

        self.total_label.grid(
            row=5,
            column=0,
            sticky="w",
            pady=10
        )

        # Change and completion buttons
        actions_frame = ttk.Frame(sale_frame)

        actions_frame.grid(
            row=6,
            column=0,
            sticky="ew",
            pady=15
        )

        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=2)

        ttk.Button(
            actions_frame,
            text="CALCULATE CHANGE",
            command=self.open_change_calculator
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 5)
        )

        ttk.Button(
            actions_frame,
            text="COMPLETE SALE",
            style="Success.TButton",
            command=self.finalize_sale
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 0)
        )

        # ---------------------------------
        # FOOTER INFORMATION
        # ---------------------------------

        ttk.Label(
            main_frame,
            text="3 additional slots available "
                 "(products 10, 11 and 12)."
        ).pack(anchor="w", pady=(15, 0))

        self.status_var = tk.StringVar(
            value="System ready."
        )

        ttk.Label(
            main_frame,
            textvariable=self.status_var
        ).pack(anchor="w", pady=(10, 0))

    def open_product_manager(self):
        """Opens the product management window."""

        manager = tk.Toplevel(self.root)
        manager.title("Product management")
        center_window(manager, 720, 800)
        manager.minsize(620, 560)
        manager.configure(bg="#F2F5F7")

        manager.transient(self.root)
        manager.grab_set()

        # Main area
        frame = ttk.Frame(
            manager,
            padding=20
        )
        frame.pack(fill="both", expand=True)

        # Title and description
        ttk.Label(
            frame,
            text="Product management",
            style="Title.TLabel"
        ).pack(anchor="w", pady=(0, 5))

        ttk.Label(
            frame,
            text="Set product names and prices."
        ).pack(anchor="w", pady=(0, 12))

        # Table area
        table_frame = ttk.LabelFrame(
            frame,
            text="Products and prices",
            padding=10
        )
        table_frame.pack(fill="both", expand=True)

        table_frame.columnconfigure(1, weight=1)

        # Headings
        ttk.Label(
            table_frame,
            text="Button",
            style="TableHeader.TLabel"
        ).grid(row=0, column=0, padx=5, pady=(3, 8))

        ttk.Label(
            table_frame,
            text="Product name",
            style="TableHeader.TLabel"
        ).grid(row=0, column=1, sticky="w", padx=5, pady=(3, 8))

        ttk.Label(
            table_frame,
            text="Price (€)",
            style="TableHeader.TLabel"
        ).grid(row=0, column=2, padx=5, pady=(3, 8))

        # Store the text fields
        entries = {}

        products = list_products()

        for product in products:
            slot = product["slot"]
            name = product["name"]
            price = product["price_cents"]

            name_var = tk.StringVar(
                value=name if name is not None else ""
            )

            if price is not None:
                price_text = f"{price // 100}.{price % 100:02d}"
            else:
                price_text = ""

            price_var = tk.StringVar(value=price_text)

            row = slot

            # Button number
            ttk.Label(
                table_frame,
                text=f"{slot:02d}"
            ).grid(
                row=row,
                column=0,
                padx=5,
                pady=3
            )

            # Product name
            ttk.Entry(
                table_frame,
                textvariable=name_var,
                width=30
            ).grid(
                row=row,
                column=1,
                sticky="ew",
                padx=5,
                pady=3
            )

            # Product price
            ttk.Entry(
                table_frame,
                textvariable=price_var,
                width=12
            ).grid(
                row=row,
                column=2,
                padx=5,
                pady=3
            )

            entries[slot] = (name_var, price_var)

        # Additional information
        ttk.Label(
            frame,
            text=(
                "Products 1 to 9 are required. "
                "For slots 10 to 12, leave both fields "
                "empty until you need them."
            ),
            wraplength=650
        ).pack(anchor="w", pady=10)

        # Bottom buttons
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=(5, 0))

        buttons.columnconfigure(0, weight=1, uniform="actions")
        buttons.columnconfigure(1, weight=1, uniform="actions")

        ttk.Button(
            buttons,
            text="Cancel",
            style="TButton",
            command=manager.destroy
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 5)
        )

        ttk.Button(
            buttons,
            text="Save changes",
            style="Success.TButton",
            command=lambda: self.save_product_changes(
                entries,
                manager
            )
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 0)
        )

    def save_product_changes(self, entries, manager):

        updates = []
        product_names = {}

        # Validate all 12 products before saving
        for slot, (name_var, price_var) in entries.items():

            name = name_var.get().strip()
            price_text = price_var.get().strip().replace(",", ".")

            # Allow empty fields only for the 3 additional slots
            if not name and not price_text:

                if slot <= 9:
                    self.show_error_dialog(
                        "Required product",
                        f"Product {slot} cannot be left blank.",
                        parent=manager
                    )
                    return

                updates.append((slot, None, None))
                continue

            # Do not allow incomplete fields
            if not name or not price_text:

                self.show_error_dialog(
                    "Incomplete information",
                    f"Check the name and price of product {slot}.",
                    parent=manager
                )
                return

            # Do not allow duplicate product names
            normalized_name = name.casefold()

            if normalized_name in product_names:

                previous_slot = product_names[normalized_name]

                self.show_error_dialog(
                    "Duplicate product",
                    (
                        f"This product name is already assigned "
                        f"to button {previous_slot}.\n\n"
                        "Each product must have a unique name."
                    ),
                    parent=manager
                )
                return

            product_names[normalized_name] = slot

            # Validate the price
            try:

                price_decimal = Decimal(price_text)

                if not price_decimal.is_finite() or price_decimal < 0:
                    raise ValueError

                rounded_price = price_decimal.quantize(
                    Decimal("0.01")
                )

                if price_decimal != rounded_price:
                    raise ValueError

                price_cents = int(rounded_price * 100)

            except (InvalidOperation, ValueError):

                self.show_error_dialog(
                    "Invalid price",
                    (
                        f"The price of product {slot} is invalid.\n\n"
                        "Enter an amount such as 1.50 or 2.00."
                    ),
                    parent=manager
                )
                return

            updates.append(
                (slot, name, price_cents)
            )

        # Save to the database
        try:

            update_products(updates)
            self.create_backup()

        except sqlite3.IntegrityError as error:

            if "UNIQUE constraint failed: products.name_normalized" in str(error):

                self.show_error_dialog(
                    "Duplicate product",
                    (
                        "A product with this name already exists.\n\n"
                        "Product names must be unique, even when they differ by "
                        "capitalisation or accents."
                    ),
                    parent=manager
                )

            else:

                self.show_error_dialog(
                    "Validation error",
                    "The product data does not meet the database constraints.",
                    parent=manager
                )

            return

        except sqlite3.Error:

            self.show_error_dialog(
                "Error",
                "Could not save the products. Please try again.",
                parent=manager
            )
            return

        # Update the main window buttons
        self.refresh_product_buttons()

        self.status_var.set(
            "Products updated successfully."
        )

        manager.destroy()

        self.show_success_dialog(
            "Success",
            "Products have been updated successfully!",
            parent=self.root
        )

    def refresh_product_buttons(self):

        products = list_products()

        for product in products:

            slot = product["slot"]
            name = product["name"]
            price = product["price_cents"]

            button = self.product_buttons[slot]

            if name is None:

                button.configure(
                    text="\n",
                    style="Empty.Product.TButton",
                    state="disabled"
                )

            else:

                button.configure(
                    text=f"{name}\n{format_money(price)}",
                    style="Product.TButton",
                    state="normal",
                    command=lambda p=product: self.add_product(p)
                )

    # ---------------------------------
    # CART FUNCTIONS
    # ---------------------------------

    def add_product(self, product):

        slot = product["slot"]
        name = product["name"]
        price = product["price_cents"]

        if name is None or price is None:
            return

        if slot in self.cart:

            self.cart[slot]["quantity"] += 1

        else:

            self.cart[slot] = {
                "name": name,
                "price_cents": price,
                "quantity": 1
            }

        self.refresh_cart()

        self.status_var.set(
            f"Adicionado: {name}"
        )

    def decrease_quantity(self):

        selected = self.cart_tree.selection()

        if not selected:
            self.status_var.set(
                "Select a product first."
            )
            return

        slot = int(selected[0])

        self.cart[slot]["quantity"] -= 1

        if self.cart[slot]["quantity"] <= 0:
            del self.cart[slot]

        self.refresh_cart()

        self.status_var.set(
            "Quantity updated."
        )

    def remove_product(self):

        selected = self.cart_tree.selection()

        if not selected:
            self.status_var.set(
                "Select a product first."
            )
            return

        slot = int(selected[0])

        name = self.cart[slot]["name"]

        del self.cart[slot]

        self.refresh_cart()

        self.status_var.set(
            f"Product removed: {name}"
        )

    def clear_cart(self):

        self.cart.clear()

        self.refresh_cart()

        self.status_var.set(
            "Sale cleared."
        )

    def refresh_cart(self):

        # Clear the table
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)

        # Calculate the total
        self.total_cents = 0

        for slot, product in self.cart.items():

            quantity = product["quantity"]
            price = product["price_cents"]

            subtotal = price * quantity

            self.total_cents += subtotal

            self.cart_tree.insert(
                "",
                "end",
                iid=str(slot),
                values=(
                    product["name"],
                    quantity,
                    format_money(price),
                    format_money(subtotal)
                )
            )

        # Update the displayed total
        self.total_label.config(
            text=format_money(self.total_cents)
        )

    def finalize_sale(self):

        # Check whether the cart contains products
        if not self.cart:

            self.show_warning_dialog(
                "Empty cart",
                "There are no products to complete the sale.",
                parent=self.root
            )

            return

        # Display the total for confirmation
        total = format_money(self.total_cents)

        confirm = self.show_confirm_dialog(
            "Complete sale",
            "Are you sure you want to record this sale?",
            total,
            parent=self.root
        )

        if not confirm:
            return

        # Save the sale
        try:

            sale_id, total_cents = save_sale(self.cart)

        except (ValueError, sqlite3.Error) as error:

            self.show_error_dialog(
                "Save error",
                f"Could not save the sale.\n\n{error}",
                parent=self.root
            )

            return

        self.create_backup()

        # Clear the cart only after saving
        self.cart.clear()

        self.refresh_cart()

        self.status_var.set(
            f"Sale #{sale_id} recorded successfully."
        )

        # Confirmar ao utilizador
        self.show_success_dialog(
            "Sale completed",
            f"Sale #{sale_id} recorded successfully!\n\n"
            f"Total: {format_money(total_cents)}",
            parent=self.root
        )

    def open_change_calculator(self):
        """Opens a calculator to determine the change due."""

        if self.total_cents <= 0:
            self.show_warning_dialog(
                "Empty cart",
                "Add products to the sale first.",
                parent=self.root
            )
            return

        # Store the current sale total
        total_cents = self.total_cents

        calculator = tk.Toplevel(self.root)
        calculator.title("Change calculator")
        calculator.configure(bg="#F2F5F7")

        center_window(calculator, 480, 460)

        calculator.resizable(False, False)
        calculator.transient(self.root)
        calculator.grab_set()

        # Main area
        frame = ttk.Frame(
            calculator,
            padding=24
        )
        frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            frame,
            text="Change calculator",
            style="Section.TLabel"
        ).pack(pady=(0, 12))

        # Sale total
        ttk.Label(
            frame,
            text="SALE TOTAL",
            font=("Segoe UI", 10, "bold")
        ).pack()

        ttk.Label(
            frame,
            text=format_money(total_cents),
            style="Total.TLabel"
        ).pack(pady=(3, 15))

        # Valor entregue pelo cliente
        ttk.Label(
            frame,
            text="Amount received from customer (€):"
        ).pack(pady=(0, 5))

        received_entry = ttk.Entry(
            frame,
            font=("Segoe UI", 16),
            justify="center",
            width=18
        )
        received_entry.pack(pady=5)
        received_entry.focus_set()

        result_var = tk.StringVar(
            value="Enter the amount received."
        )

        # Calculate the change due
        def calculate_change():
            """Calculates change in cents."""

            received_text = (
                received_entry.get().strip().replace(",", ".")
            )

            try:
                received_amount = Decimal(received_text)

                if (
                    not received_amount.is_finite()
                    or received_amount < 0
                ):
                    raise ValueError

                rounded_amount = received_amount.quantize(
                    Decimal("0.01")
                )

                if received_amount != rounded_amount:
                    result_var.set(
                        "Use no more than two decimal places."
                    )
                    return

                received_cents = int(rounded_amount * 100)

            except (InvalidOperation, ValueError):
                result_var.set(
                    "Enter a valid amount, for example 10.00."
                )
                return

            if received_cents < total_cents:
                missing_cents = total_cents - received_cents

                result_var.set(
                    f"Still due: {format_money(missing_cents)}"
                )
                return

            change_cents = received_cents - total_cents

            result_var.set(
                f"Change to return: {format_money(change_cents)}"
            )

        # Quick amount buttons
        quick_frame = ttk.Frame(frame)
        quick_frame.pack(pady=12)

        def set_quick_amount(amount):
            """Preenche o valor recebido e calcula automaticamente."""

            received_entry.delete(0, tk.END)
            received_entry.insert(0, f"{amount}.00")

            calculate_change()

        for amount in (5, 10, 20, 50, 100):
            ttk.Button(
                quick_frame,
                text=f"{amount} €",
                width=7,
                command=lambda value=amount: set_quick_amount(value)
            ).pack(side="left", padx=3)

        # Resultado
        ttk.Label(
            frame,
            textvariable=result_var,
            style="Section.TLabel"
        ).pack(pady=12)

        # Action buttons
        buttons_frame = ttk.Frame(frame)
        buttons_frame.pack(fill="x", pady=(5, 0))

        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)

        ttk.Button(
            buttons_frame,
            text="Close",
            style="TButton",
            command=calculator.destroy
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 5)
        )

        ttk.Button(
            buttons_frame,
            text="CALCULATE",
            style="Success.TButton",
            command=calculate_change
        ).grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 0)
        )

        # Keyboard shortcuts
        calculator.bind(
            "<Return>",
            lambda event: calculate_change()
        )

        calculator.bind(
            "<Escape>",
            lambda event: calculator.destroy()
        )

    def create_backup(self):
        """Updates the backup and displays a warning if an error occurs."""

        try:
            create_database_backup()

        except (sqlite3.Error, OSError) as error:
            self.show_warning_dialog(
                "Backup warning",
                "The data was saved, but could not "
                "update the backup.\n\n"
                f"Error: {error}",
                parent=self.root
            )
            return False

        self.status_var.set("Backup updated.")
        return True

    def open_admin(self):
        AdminWindow(self.root)

    def run(self):

        self.root.mainloop()


if __name__ == "__main__":
    application = POSApp()
    application.run()
