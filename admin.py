import calendar
import sqlite3
import subprocess
import sys
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from database import (
    BACKUP_DIR,
    export_sales_data,
    get_admin_lockout_state,
    get_daily_sales_summary,
    get_sale_details,
    list_sales,
    restore_database_backup,
    save_admin_lockout_state,
)
from exporter import save_sales_csv
from security import change_pin, pin_requires_change, verify_pin
from window_utils import center_window

# Application fonts
FONT_NORMAL = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_SUBTITLE = ("Segoe UI", 15, "bold")
FONT_TITLE = ("Segoe UI", 22, "bold")
FONT_TOTAL = ("Segoe UI", 24, "bold")

def format_money(cents):
    """Converts cents to euros."""
    euros = cents / 100
    return f"€{euros:,.2f}"


class AdminWindow:
    def __init__(self, parent):
        self.parent = parent

        if not self.authenticate():
            return

        self.window = tk.Toplevel(parent)
        self.window.title("Administration")
        center_window(self.window, 450, 500)
        self.window.resizable(False, False)

        self.create_interface()

    def ask_pin_dialog(self, title, prompt, require_six_digits=False):
        """Displays a custom dialog for entering the PIN."""

        background = "#F2F5F7"
        navy = "#183B4E"

        dialog = tk.Toplevel(self.parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(self.parent)

        result: dict[str, str | None] = {"pin": None}

        # Window styles
        style = ttk.Style(dialog)

        style.configure(
            "Pin.TFrame",
            background=background
        )

        style.configure(
            "Pin.Title.TLabel",
            font=FONT_SUBTITLE,
            background=background,
            foreground=navy
        )

        style.configure(
            "Pin.Prompt.TLabel",
            font=FONT_NORMAL,
            background=background,
            foreground=navy
        )

        # Main area
        frame = ttk.Frame(
            dialog,
            style="Pin.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=title,
            style="Pin.Title.TLabel"
        ).pack(pady=(0, 12))

        ttk.Label(
            frame,
            text=prompt,
            style="Pin.Prompt.TLabel"
        ).pack(pady=(0, 8))

        pin_var = tk.StringVar(master=dialog)

        pin_entry = ttk.Entry(
            frame,
            textvariable=pin_var,
            show="*",
            font=("Segoe UI", 16),
            justify="center",
            width=18
        )
        pin_entry.pack(pady=(0, 8 if require_six_digits else 18))

        # Validation label for the new PIN fields.
        pin_status = ttk.Label(
            frame,
            text="The PIN must contain exactly 6 digits.",
            style="Pin.Prompt.TLabel"
        )

        if require_six_digits:
            pin_status.pack(pady=(0, 10))

        # Button handlers
        def accept():
            value = pin_var.get()

            if require_six_digits and not (
                len(value) == 6
                and value.isascii()
                and value.isdigit()
            ):
                return

            result["pin"] = value
            dialog.destroy()

        def cancel():
            dialog.destroy()

        # Buttons
        buttons = ttk.Frame(
            frame,
            style="Pin.TFrame"
        )
        buttons.pack(fill="x")

        buttons.columnconfigure(0, weight=1, uniform="actions")
        buttons.columnconfigure(1, weight=1, uniform="actions")

        ttk.Button(
            buttons,
            text="Cancel",
            style="TButton",
            command=cancel
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 5)
        )

        accept_button = ttk.Button(
            buttons,
            text="Log in",
            style="Success.TButton",
            command=accept,
            state="disabled" if require_six_digits else "normal"
        )
        accept_button.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(5, 0)
        )

        if require_six_digits:
            def validate_new_pin(*args):
                value = pin_var.get()
                valid = (
                    len(value) == 6
                    and value.isascii()
                    and value.isdigit()
                )

                if valid:
                    pin_status.configure(
                        text="Valid PIN.",
                        foreground="#21865B"
                    )
                    accept_button.configure(state="normal")
                else:
                    pin_status.configure(
                        text="The PIN must contain exactly 6 digits.",
                        foreground="#C94C4C"
                    )
                    accept_button.configure(state="disabled")

            pin_var.trace_add("write", validate_new_pin)

        # Keyboard shortcuts
        pin_entry.bind(
            "<Return>",
            lambda event: accept()
        )

        dialog.bind(
            "<Escape>",
            lambda event: cancel()
        )

        dialog.protocol("WM_DELETE_WINDOW", cancel)

        center_window(dialog, 410, 250)

        dialog.wait_visibility()
        dialog.grab_set()
        pin_entry.focus_set()
        dialog.wait_window()

        return result["pin"]

    def show_success_dialog(self, title, message, parent=None):
        """Displays a success message using the application theme."""

        background = "#F2F5F7"
        navy = "#183B4E"
        green = "#21865B"

        if parent is None:
            parent = self.window if hasattr(self, "window") else self.parent

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        style = ttk.Style(dialog)
        style.configure(
            "SuccessDialog.TFrame",
            background=background
        )
        style.configure(
            "SuccessDialog.Title.TLabel",
            font=FONT_SUBTITLE,
            background=background,
            foreground=green
        )
        style.configure(
            "SuccessDialog.Message.TLabel",
            font=FONT_NORMAL,
            background=background,
            foreground=navy
        )

        frame = ttk.Frame(
            dialog,
            style="SuccessDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=title,
            style="SuccessDialog.Title.TLabel"
        ).grid(row=0, column=0, pady=(5, 15))

        ttk.Label(
            frame,
            text=message,
            style="SuccessDialog.Message.TLabel",
            justify="center",
            wraplength=460
        ).grid(row=1, column=0, sticky="n", pady=(0, 10))

        ttk.Button(
            frame,
            text="OK",
            style="Success.TButton",
            command=dialog.destroy,
            width=12
        ).grid(row=2, column=0, sticky="s", pady=(10, 0))

        center_window(dialog, 520, 340)

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
            parent = self.window if hasattr(self, "window") else self.parent

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        style = ttk.Style(dialog)
        style.configure(
            "ErrorDialog.TFrame",
            background=background
        )
        style.configure(
            "ErrorDialog.Title.TLabel",
            font=FONT_SUBTITLE,
            background=background,
            foreground=red
        )
        style.configure(
            "ErrorDialog.Message.TLabel",
            font=FONT_NORMAL,
            background=background,
            foreground=navy
        )

        frame = ttk.Frame(
            dialog,
            style="ErrorDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=title,
            style="ErrorDialog.Title.TLabel"
        ).grid(row=0, column=0, pady=(5, 15))

        ttk.Label(
            frame,
            text=message,
            style="ErrorDialog.Message.TLabel",
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

    def show_confirm_dialog(self, title, message, parent=None):
        """Displays a confirmation dialog using the application theme."""

        background = "#F2F5F7"
        navy = "#183B4E"

        if parent is None:
            parent = self.window if hasattr(self, "window") else self.parent

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        result = {"confirmed": False}

        style = ttk.Style(dialog)
        style.configure(
            "ConfirmDialog.TFrame",
            background=background
        )
        style.configure(
            "ConfirmDialog.Title.TLabel",
            font=FONT_SUBTITLE,
            background=background,
            foreground=navy
        )
        style.configure(
            "ConfirmDialog.Message.TLabel",
            font=FONT_NORMAL,
            background=background,
            foreground=navy
        )

        frame = ttk.Frame(
            dialog,
            style="ConfirmDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text=title,
            style="ConfirmDialog.Title.TLabel"
        ).pack(pady=(5, 15))

        ttk.Label(
            frame,
            text=message,
            style="ConfirmDialog.Message.TLabel",
            justify="center",
            wraplength=460
        ).pack(pady=(0, 20))

        buttons_frame = ttk.Frame(
            frame,
            style="ConfirmDialog.TFrame"
        )
        buttons_frame.pack(fill="x")

        def cancel():
            dialog.destroy()

        def confirm():
            result["confirmed"] = True
            dialog.destroy()

        ttk.Button(
            buttons_frame,
            text="Cancel",
            style="Admin.TButton",
            command=cancel
        ).pack(side="left", expand=True, fill="x", padx=(0, 5))

        ttk.Button(
            buttons_frame,
            text="Confirmar",
            style="Admin.Danger.TButton",
            command=confirm
        ).pack(side="left", expand=True, fill="x", padx=(5, 0))

        dialog.protocol("WM_DELETE_WINDOW", cancel)
        dialog.bind("<Escape>", lambda event: cancel())
        dialog.bind("<Return>", lambda event: confirm())

        center_window(dialog, 520, 420)

        dialog.wait_visibility()
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

        return result["confirmed"]

    def show_warning_dialog(self, title, message, parent=None):
        """Displays a warning message using the administration theme."""

        background = "#F2F5F7"
        navy = "#183B4E"
        orange = "#C47A16"

        if parent is None:
            parent = self.window

        dialog = tk.Toplevel(parent)
        dialog.title(title)
        dialog.configure(bg=background)
        dialog.resizable(False, False)
        dialog.transient(parent)

        style = ttk.Style(dialog)
        style.configure(
            "AdminWarningDialog.TFrame",
            background=background
        )
        style.configure(
            "AdminWarningDialog.Title.TLabel",
            font=FONT_SUBTITLE,
            background=background,
            foreground=orange
        )
        style.configure(
            "AdminWarningDialog.Message.TLabel",
            font=FONT_NORMAL,
            background=background,
            foreground=navy
        )

        frame = ttk.Frame(
            dialog,
            style="AdminWarningDialog.TFrame",
            padding=25
        )
        frame.pack(fill="both", expand=True)

        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=title,
            style="AdminWarningDialog.Title.TLabel"
        ).grid(row=0, column=0, pady=(5, 15))

        ttk.Label(
            frame,
            text=message,
            style="AdminWarningDialog.Message.TLabel",
            justify="center",
            wraplength=460
        ).grid(row=1, column=0, sticky="n", pady=(0, 10))

        ttk.Button(
            frame,
            text="OK",
            style="Admin.TButton",
            command=dialog.destroy,
            width=12
        ).grid(row=2, column=0, sticky="s", pady=(10, 0))

        center_window(dialog, 520, 300)

        dialog.wait_visibility()
        dialog.grab_set()
        dialog.focus_set()
        dialog.wait_window()

    def authenticate(self):
        """Requests the PIN and locks access after five failed attempts."""

        failed_attempts, locked_until = get_admin_lockout_state()
        now = datetime.now()

        # Verificar se existe um bloqueio ativo.
        if locked_until:
            try:
                lock_expiry = datetime.fromisoformat(locked_until)
            except ValueError:
                # Correct any invalid lockout value.
                failed_attempts = 0
                save_admin_lockout_state(0, "")
            else:
                if now < lock_expiry:
                    remaining_seconds = int(
                        (lock_expiry - now).total_seconds()
                    )
                    remaining_minutes = max(
                        1,
                        (remaining_seconds + 59) // 60
                    )

                    self.show_warning_dialog(
                        "Access temporarily locked",
                        (
                            "Administration access is locked.\n\n"
                            f"Please try again in approximately "
                            f"{remaining_minutes} minutes."
                        ),
                        parent=self.parent
                    )
                    return False

                # The lockout period has expired.
                failed_attempts = 0
                save_admin_lockout_state(0, "")

        pin = self.ask_pin_dialog(
            "Administration access",
            "Enter the administrator PIN:"
        )

        # Cancelling does not count as a failed attempt.
        if pin is None:
            return False

        if not verify_pin(pin):
            failed_attempts += 1

            if failed_attempts >= 5:
                lock_expiry = datetime.now() + timedelta(minutes=5)

                save_admin_lockout_state(
                    failed_attempts,
                    lock_expiry.isoformat(timespec="seconds")
                )

                self.show_error_dialog(
                    "Access locked",
                    (
                        "You have reached the limit of five "
                        "incorrect PIN attempts.\n\n"
                        "Access will be locked for 5 minutes."
                    ),
                    parent=self.parent
                )
            else:
                save_admin_lockout_state(failed_attempts, "")

                attempts_left = 5 - failed_attempts

                self.show_error_dialog(
                    "Access denied",
                    (
                        "Incorrect PIN.\n\n"
                        f"You have {attempts_left} attempt(s) "
                        "remaining before access is locked."
                    ),
                    parent=self.parent
                )
            return False

        # Correct PIN: clear previous failed attempts.
        save_admin_lockout_state(0, "")

        return not pin_requires_change() or self.change_initial_pin()

    def change_initial_pin(self):
        """Requires the initial PIN to be changed."""

        new_pin = self.ask_pin_dialog(
            "New PIN",
            "Enter the new 6-digit PIN:",
            require_six_digits=True
        )

        if new_pin is None:
            return False

        confirm_pin = self.ask_pin_dialog(
            "Confirm PIN",
            "Enter the new PIN again:",
            require_six_digits=True
        )

        if confirm_pin is None:
            return False

        if new_pin != confirm_pin:
            self.show_error_dialog(
                "PIN not changed",
                "The entered PINs do not match.",
                parent=self.parent
            )
            return False

        try:
            change_pin(new_pin)

        except ValueError as error:
            self.show_error_dialog(
                "Invalid PIN",
                str(error),
                parent=self.parent
            )
            return False

        self.show_success_dialog(
            "PIN changed",
            "The administrator PIN was changed successfully.",
            parent=self.parent
        )

        return True

    def create_interface(self):
        """Creates the main administration window."""

        background = "#F2F5F7"
        navy = "#183B4E"
        white = "#FFFFFF"
        border = "#D7E0E5"
        red = "#C94C4C"
        red_dark = "#A83B3B"

        self.window.configure(bg=background)

        # Configure administration styles
        style = ttk.Style(self.window)

        style.configure(
            "Admin.TFrame",
            background=background
        )

        style.configure(
            "Admin.Title.TLabel",
            font=FONT_TITLE,
            background=background,
            foreground=navy
        )

        style.configure(
            "Admin.TButton",
            font=FONT_BUTTON,
            background=white,
            foreground=navy,
            padding=(14, 10),
            borderwidth=1,
            bordercolor=border
        )

        style.map(
            "Admin.TButton",
            background=[
                ("pressed", "#116C62"),
                ("active", "#E2F0ED")
            ],
            foreground=[
                ("pressed", white),
                ("active", navy)
            ]
        )

        style.configure(
            "Admin.Danger.TButton",
            font=FONT_BUTTON,
            background=red,
            foreground=white,
            padding=(14, 10),
            borderwidth=0
        )

        style.map(
            "Admin.Danger.TButton",
            background=[
                ("pressed", red_dark),
                ("active", red_dark)
            ]
        )

        style.configure(
            "Admin.Subtitle.TLabel",
            font=FONT_SUBTITLE,
            background=background,
            foreground=navy
        )

        style.configure(
            "Admin.Total.TLabel",
            font=FONT_TOTAL,
            background=background,
            foreground=navy
        )

        # Main area
        frame = ttk.Frame(
            self.window,
            style="Admin.TFrame",
            padding=(32, 25)
        )
        frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            frame,
            text="Administration",
            style="Admin.Title.TLabel"
        ).pack(pady=(8, 22))

        # View sales
        ttk.Button(
            frame,
            text="View sales",
            style="Admin.TButton",
            command=self.open_sales
        ).pack(fill="x", pady=7)

        # Daily summary
        ttk.Button(
            frame,
            text="Daily sales summary",
            style="Admin.TButton",
            command=self.open_daily_summary
        ).pack(fill="x", pady=7)

        # Export sales
        ttk.Button(
            frame,
            text="Export sales",
            style="Admin.TButton",
            command=self.open_export_dialog
        ).pack(fill="x", pady=7)

        # Change administrator PIN
        ttk.Button(
            frame,
            text="Change administrator PIN",
            style="Admin.TButton",
            command=self.change_admin_pin
        ).pack(fill="x", pady=7)

        style.configure(
            "Admin.TLabel",
            font=FONT_NORMAL,
            background=background,
            foreground=navy
        )

        style.configure(
            "Admin.TLabelframe",
            background=background,
            bordercolor=border
        )

        style.configure(
            "Admin.TLabelframe.Label",
            font=FONT_BUTTON,
            background=background,
            foreground=navy
        )

        style.configure(
            "Admin.TRadiobutton",
            font=FONT_NORMAL,
            background=background,
            foreground=navy,
            padding=(4, 5)
        )

        style.configure(
            "Admin.TEntry",
            font=FONT_NORMAL,
            fieldbackground=white,
            foreground=navy,
            padding=7
        )

        style.configure(
            "Admin.Success.TButton",
            font=FONT_BUTTON,
            background="#21865B",
            foreground=white,
            padding=(16, 10),
            borderwidth=0
        )

        style.map(
            "Admin.Success.TButton",
            background=[
                ("pressed", "#196B48"),
                ("active", "#196B48")
            ]
        )

        # Restore backup
        ttk.Button(
            frame,
            text="Restore backup",
            style="Admin.Danger.TButton",
            command=self.restore_backup
        ).pack(fill="x", pady=7)

        # Close administration
        ttk.Button(
            frame,
            text="Close",
            style="Admin.TButton",
            command=self.window.destroy
        ).pack(fill="x", pady=(12, 0))

    def open_sales(self):
        """Displays the sales history."""

        sales_window = tk.Toplevel(self.window)
        sales_window.title("Sales history")
        center_window(sales_window, 855, 550)
        sales_window.minsize(700, 450)

        sales_window.configure(bg="#F2F5F7")

        # Main area
        frame = ttk.Frame(
            sales_window,
            style="Admin.TFrame",
            padding=20
        )
        frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            frame,
            text="Sales history",
            style="Admin.Subtitle.TLabel"
        ).pack(anchor="w", pady=(0, 15))

        # Table area
        table_frame = ttk.Frame(
            frame,
            style="Admin.TFrame"
        )
        table_frame.pack(fill="both", expand=True)

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("id", "date", "total")

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )

        tree.heading("id", text="Sale no.")
        tree.heading("date", text="Date and time")
        tree.heading("total", text="Total")

        tree.column("id", width=90, anchor="center")
        tree.column("date", width=350, anchor="center")
        tree.column("total", width=150, anchor="e")

        tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        tree.configure(yscrollcommand=scrollbar.set)

        # View sales
        try:
            sales = list_sales()

        except sqlite3.Error as error:
            self.show_error_dialog(
                "Datebase error",
                f"Could not retrieve sales:\n{error}",
                parent=sales_window
            )
            sales_window.destroy()
            return


        # Populate the table with sales
        for sale in sales:
            tree.insert(
                "",
                "end",
                iid=str(sale["id"]),
                values=(
                    sale["id"],
                    sale["created_at"],
                    format_money(sale["total_cents"])
                )
            )

        # Open details for the selected sale
        def open_selected_sale(event=None):
            selection = tree.selection()

            if not selection:
                messagebox.showinfo(
                    "Select a sale",
                    "Select a sale first.",
                    parent=sales_window
                )
                return

            sale_id = int(selection[0])
            self.show_sale_details(sale_id, sales_window)

        # Bottom button — created only once
        ttk.Button(
            frame,
            text="View details of selected sale",
            style="Admin.TButton",
            command=open_selected_sale,
            state="normal" if sales else "disabled"
        ).pack(fill="x", pady=(15, 0))

        # Double-click the table
        tree.bind("<Double-1>", open_selected_sale)

        # Message shown when there are no sales yet
        if not sales:
            ttk.Label(
                frame,
                text="No sales have been recorded yet.",
                style="Admin.Subtitle.TLabel"
            ).pack(pady=15)


        def open_selected_sale(event=None):
            selection = tree.selection()

            if not selection:
                messagebox.showinfo(
                    "Select a sale",
                    "Select a sale first.",
                    parent=sales_window
                )
                return

            sale_id = int(selection[0])
            self.show_sale_details(sale_id, sales_window)

        details_button = tk.Button(
            sales_window,
            text="View details of selected sale",
            font=FONT_BUTTON,
            command=open_selected_sale
        )
        details_button.pack(pady=10)

        tree.bind("<Double-1>", open_selected_sale)

        if not sales:
            tk.Label(
                sales_window,
                text="No sales have been recorded yet."
            ).pack(pady=10)

    def show_sale_details(self, sale_id, parent):
        """Displays the products and total for a sale."""

        result = get_sale_details(sale_id)

        if result is None:
            self.show_error_dialog(
                "Error",
                "Could not find this sale.",
                parent=parent
            )
            return

        sale, items = result

        details_window = tk.Toplevel(parent)
        details_window.title(f"Sale details #{sale_id}")
        center_window(details_window, 700, 450)
        details_window.minsize(600, 380)
        details_window.configure(bg="#F2F5F7")

        # Main area
        frame = ttk.Frame(
            details_window,
            style="Admin.TFrame",
            padding=20
        )
        frame.pack(fill="both", expand=True)

        # Sale information
        ttk.Label(
            frame,
            text=f"Sale no. {sale['id']}",
            style="Admin.Subtitle.TLabel"
        ).pack(anchor="w", pady=(0, 5))

        ttk.Label(
            frame,
            text=f"Date and time: {sale['created_at']}",
            font=FONT_NORMAL
        ).pack(anchor="w", pady=(0, 15))

        # Products table
        columns = ("product", "quantity", "price", "subtotal")

        tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings",
            height=10
        )

        tree.heading("product", text="Product")
        tree.heading("quantity", text="Quantity")
        tree.heading("price", text="Unit price")
        tree.heading("subtotal", text="Subtotal")

        tree.column("product", width=220)
        tree.column("quantity", width=100, anchor="center")
        tree.column("price", width=130, anchor="e")
        tree.column("subtotal", width=130, anchor="e")

        tree.pack(fill="both", expand=True)

        for item in items:
            tree.insert(
                "",
                "end",
                values=(
                    item["product_name"],
                    item["quantity"],
                    format_money(item["unit_price_cents"]),
                    format_money(item["subtotal_cents"])
                )
            )

        # Sale total
        ttk.Label(
            frame,
            text=f"TOTAL: {format_money(sale['total_cents'])}",
            style="Admin.Total.TLabel"
        ).pack(anchor="e", pady=(15, 0))

    def open_daily_summary(self):
        """Displays the daily sales summary."""

        summary_window = tk.Toplevel(self.window)
        summary_window.title("Daily sales summary")
        center_window(summary_window, 650, 450)
        summary_window.minsize(550, 350)
        summary_window.configure(bg="#F2F5F7")

        # Main area
        frame = ttk.Frame(
            summary_window,
            style="Admin.TFrame",
            padding=20
        )
        frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            frame,
            text="Daily sales summary",
            style="Admin.Subtitle.TLabel"
        ).pack(anchor="w", pady=(0, 15))

        # Table area
        table_frame = ttk.Frame(
            frame,
            style="Admin.TFrame"
        )
        table_frame.pack(fill="both", expand=True)

        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        columns = ("date", "count", "total")

        tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=12
        )

        tree.heading("date", text="Date")
        tree.heading("count", text="Number of sales")
        tree.heading("total", text="Total revenue")

        tree.column("date", width=200, anchor="center")
        tree.column("count", width=150, anchor="center")
        tree.column("total", width=180, anchor="e")

        tree.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        # Scrollbar
        scrollbar = ttk.Scrollbar(
            table_frame,
            orient="vertical",
            command=tree.yview
        )
        scrollbar.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        tree.configure(yscrollcommand=scrollbar.set)

        # Retrieve the daily summary
        try:
            days = get_daily_sales_summary()

        except sqlite3.Error as error:
            self.show_error_dialog(
                "Datebase error",
                f"Could not retrieve the summary:\n{error}",
                parent=summary_window
            )
            summary_window.destroy()
            return

        # Populate the table
        for day in days:
            tree.insert(
                "",
                "end",
                values=(
                    day["sale_date"],
                    day["sales_count"],
                    format_money(day["total_cents"])
                )
            )

        if not days:
            ttk.Label(
                frame,
                text="No sales have been recorded yet.",
                font=FONT_NORMAL
            ).pack(pady=15)

    def open_export_dialog(self):
        """Allows sales to be exported to CSV for a selected period."""

        dialog = tk.Toplevel(self.window)
        dialog.title("Export sales")
        center_window(dialog, 470, 500)
        dialog.resizable(False, False)
        dialog.configure(bg="#F2F5F7")

        # Main area
        frame = ttk.Frame(
            dialog,
            style="Admin.TFrame",
            padding=22
        )
        frame.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            frame,
            text="Export sales",
            style="Admin.Subtitle.TLabel"
        ).pack(anchor="w", pady=(0, 15))

        period_var = tk.StringVar(
            master=dialog,
            value="all"
        )

        # Period selection
        period_frame = ttk.LabelFrame(
            frame,
            text="Select period",
            style="Admin.TLabelframe",
            padding=12
        )
        period_frame.pack(fill="x", pady=5)

        options = [
            ("All sales", "all"),
            ("Today", "today"),
            ("This month", "month"),
            ("Custom period", "custom")
        ]

        for label, value in options:
            ttk.Radiobutton(
                period_frame,
                text=label,
                variable=period_var,
                value=value,
                style="Admin.TRadiobutton"
            ).pack(anchor="w", pady=2)

        # Custom dates
        dates_frame = ttk.LabelFrame(
            frame,
            text="Custom dates (YYYY-MM-DD)",
            style="Admin.TLabelframe",
            padding=12
        )
        dates_frame.pack(fill="x", pady=10)

        dates_frame.columnconfigure(1, weight=1)

        today = date.today()

        ttk.Label(
            dates_frame,
            text="Start date:",
            style="Admin.TLabel"
        ).grid(row=0, column=0, sticky="w", pady=6)

        start_entry = ttk.Entry(
            dates_frame,
            width=18,
            font=FONT_NORMAL,
            style="Admin.TEntry"
        )
        start_entry.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=6
        )
        start_entry.insert(0, today.isoformat())

        ttk.Label(
            dates_frame,
            text="End date:",
            style="Admin.TLabel"
        ).grid(row=1, column=0, sticky="w", pady=6)

        end_entry = ttk.Entry(
            dates_frame,
            width=18,
            font=FONT_NORMAL,
            style="Admin.TEntry"
        )
        end_entry.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(12, 0),
            pady=6
        )
        end_entry.insert(0, today.isoformat())

        # Enable or disable the date fields
        def update_date_fields(*args):
            state = (
                "normal"
                if period_var.get() == "custom"
                else "disabled"
            )

            start_entry.configure(state=state)
            end_entry.configure(state=state)

        period_var.trace_add("write", update_date_fields)
        update_date_fields()

        # Export process
        def export_file():
            selected_period = period_var.get()
            start_date = None
            end_date = None

            if selected_period == "today":
                start_date = today.isoformat()
                end_date = today.isoformat()
                filename = f"sales_{today.isoformat()}.csv"

            elif selected_period == "month":
                first_day = today.replace(day=1)

                last_day = today.replace(
                    day=calendar.monthrange(
                        today.year,
                        today.month
                    )[1]
                )

                start_date = first_day.isoformat()
                end_date = last_day.isoformat()
                filename = f"sales_{today.strftime('%Y-%m')}.csv"

            elif selected_period == "custom":
                try:
                    start = date.fromisoformat(
                        start_entry.get().strip()
                    )
                    end = date.fromisoformat(
                        end_entry.get().strip()
                    )

                except ValueError:
                    self.show_error_dialog(
                        "Invalid dates",
                        "Enter dates in YYYY-MM-DD format.",
                        parent=dialog
                    )
                    return

                if start > end:
                    self.show_error_dialog(
                        "Invalid period",
                        "The start date cannot be later "
                        "than the end date.",
                        parent=dialog
                    )
                    return

                start_date = start.isoformat()
                end_date = end.isoformat()

                filename = (
                    f"sales_{start_date}_to_{end_date}.csv"
                )

            else:
                filename = "sales_all.csv"

            try:
                sales_data = export_sales_data(
                    start_date,
                    end_date
                )

            except sqlite3.Error as error:
                self.show_error_dialog(
                    "Datebase error",
                    f"Could not retrieve sales:\n{error}",
                    parent=dialog
                )
                return

            if not sales_data:
                messagebox.showinfo(
                    "No sales",
                    "There are no sales in the selected period.",
                    parent=dialog
                )
                return

            file_path = filedialog.asksaveasfilename(
                parent=dialog,
                title="Save export",
                initialfile=filename,
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("All files", "*.*")
                ]
            )

            if not file_path:
                return

            try:
                save_sales_csv(sales_data, file_path)

            except OSError as error:
                self.show_error_dialog(
                    "Save error",
                    f"Could not save the file:\n{error}",
                    parent=dialog
                )
                return

            self.show_success_dialog(
                "Export completed",
                f"Exported {len(sales_data)} product rows "
                "\n\n"
                f"File saved to:\n{file_path}",
                parent=dialog
            )

            dialog.destroy()

        # Bottom buttons
        buttons_frame = ttk.Frame(
            frame,
            style="Admin.TFrame"
        )
        buttons_frame.pack(fill="x", pady=(12, 0))

        ttk.Button(
            buttons_frame,
            text="Cancel",
            style="Admin.TButton",
            command=dialog.destroy
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ttk.Button(
            buttons_frame,
            text="Export CSV",
            style="Admin.Success.TButton",
            command=export_file
        ).pack(side="right", fill="x", expand=True, padx=(5, 0))

    def restore_backup(self):
        """Restores a backup and automatically restarts the POS."""

        backup_dir = BACKUP_DIR

        backup_path = filedialog.askopenfilename(
            parent=self.window,
            title="Select backup",
            initialdir=backup_dir if backup_dir.exists() else Path.home(),
            filetypes=[
                ("SQLite databases", "*.sqlite3"),
                ("All files", "*.*")
            ]
        )

        if not backup_path:
            return

        confirm = self.show_confirm_dialog(
            "Confirm restore",
            "WARNING!\n\n"
            "The current database will be replaced with the selected backup.\n\n"
            "A backup of the current database will be created first.\n\n"
            "Make sure there is no sale in progress.\n\n"
            "The POS will restart automatically after the restore.\n\n"
            "Do you want to continue?"
        )

        if not confirm:
            return

        try:
            safety_path = restore_database_backup(backup_path)

        except (FileNotFoundError, sqlite3.Error, OSError) as error:
            self.show_error_dialog(
                "Restore error",
                f"Could not restore the backup:\n\n{error}",
                parent=self.window
            )
            return

        self.show_success_dialog(
            "Restore completed",
            "The backup was restored successfully.\n\n"
            "A backup of the previous database was also saved to:\n"
            f"{safety_path}\n\n"
            "The POS will restart automatically.",
            parent=self.window
        )

        try:
            if getattr(sys, "frozen", False):
                # Application running as an executable file
                command = [sys.executable, *sys.argv[1:]]
                working_directory = Path(sys.executable).resolve().parent

            else:
                # Application running through Python
                script_path = Path(sys.argv[0]).resolve()
                command = [
                    sys.executable,
                    str(script_path),
                    *sys.argv[1:]
                ]
                working_directory = Path(__file__).resolve().parent

            subprocess.Popen(
                command,
                cwd=working_directory
            )

        except OSError as error:
            self.show_warning_dialog(
                "Restart failed",
                "The restore completed, but the POS could not "
                "restart automatically.\n\n"
                f"Error: {error}\n\n"
                "Close and reopen the POS manually.",
                parent=self.window
            )
            return

        self.parent.destroy()

    def change_admin_pin(self):
        """Allows the administrator to change their PIN."""

        # Request the current PIN to confirm identity.
        current_pin = self.ask_pin_dialog(
            "Confirm identity",
            "Enter the current administrator PIN:"
        )

        if current_pin is None:
            return

        # Verify the current PIN.
        if not verify_pin(current_pin):
            failed_attempts, _ = get_admin_lockout_state()
            failed_attempts += 1

            if failed_attempts >= 5:
                lock_expiry = datetime.now() + timedelta(minutes=5)

                save_admin_lockout_state(
                    failed_attempts,
                    lock_expiry.isoformat(timespec="seconds")
                )

                self.show_error_dialog(
                    "Access locked",
                    "You have reached five failed attempts.\n\n"
                    "The Administration window will close "
                    "and access will be locked for 5 minutes.",
                    parent=self.window
                )

                self.window.destroy()
                return

            save_admin_lockout_state(failed_attempts, "")

            attempts_left = 5 - failed_attempts

            self.show_error_dialog(
                "Incorrect PIN",
                f"Incorrect PIN.\n\n"
                f"You have {attempts_left} tentativa(s).",
                parent=self.window
            )
            return

        # Correct PIN: clear failed attempts.
        save_admin_lockout_state(0, "")

        new_pin = self.ask_pin_dialog(
            "Change PIN",
            "Enter the new 6-digit PIN:",
            require_six_digits=True
        )

        if new_pin is None:
            return

        confirm_pin = self.ask_pin_dialog(
            "Confirm new PIN",
            "Enter the new PIN again:",
            require_six_digits=True
        )

        if confirm_pin is None:
            return

        if new_pin != confirm_pin:
            self.show_error_dialog(
                "PIN not changed",
                "The entered PINs do not match.",
                parent=self.window
            )
            return

        try:
            change_pin(new_pin)

        except ValueError as error:
            self.show_error_dialog(
                "Invalid PIN",
                str(error),
                parent=self.window
            )
            return

        self.show_success_dialog(
            "PIN changed",
            "The administrator PIN was changed successfully.",
            parent=self.window
        )
