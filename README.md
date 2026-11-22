# POS Bar System

An open-source point of sale (POS) application built with Python for bars and restaurants. It provides a simple way to manage products, record sales, review sales history and keep database backups.

## Features

- **Point of sale interface:** select products using on-screen buttons.
- **Product management:** configure the names and prices of up to 12 products.
- **Shopping cart:** add products, change quantities, remove items and calculate totals.
- **Sales recording:** store each sale and its item details in SQLite.
- **Administrator access:** PIN-protected administration area, with an enforced PIN change during first-time setup.
- **Sales history:** review completed sales and their details.
- **Daily summary:** view the number of sales and total revenue per day.
- **CSV export:** export sales for a selected date range.
- **Change calculator:** calculate the change due to a customer.
- **Database backups:** create daily backups, restore a backup and retain recent copies.

## Technology

- Python 3.14 or later
- Tkinter
- SQLite
- [uv](https://docs.astral.sh/uv/) for project and environment management
- PyInstaller for Windows executable builds

## Getting started

Install Python 3.14 or later and [uv](https://docs.astral.sh/uv/getting-started/installation/). Then, from the project directory, run:

```bash
uv sync
uv run python main.py
```

## First-time administrator setup

The initial administrator PIN is **482731**. On the first access to the Administration area, the application requires you to replace it with your own six-digit PIN. Do not continue using the initial PIN.

## Running the integrity tests

```bash
uv run python test_integrity.py
```

The tests use a temporary SQLite database and do not modify the application database.

## Building the Windows executable

```bash
uv run pyinstaller --name POS-Bar --windowed --onedir main.py
```

The complete `dist/POS-Bar/` folder is required to run an onedir build. Distribute the folder contents together, for example as a ZIP archive.

## Data and backups

During development, the SQLite database is stored in the project's `data/` directory. When running the frozen Windows executable, application data is stored under `%LOCALAPPDATA%\POS-Bar`. Database backups are stored in the `backups` subdirectory.

## Project structure

```text
pos-bar-system/
├── app.py
├── admin.py
├── database.py
├── security.py
├── exporter.py
├── window_utils.py
├── main.py
├── test_integrity.py
├── .gitignore
├── .python-version
├── pyproject.toml
├── uv.lock
├── README.md
└── LICENSE
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
