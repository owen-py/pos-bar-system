def center_window(window, width, height):
    """Sizes and centres a window on the screen."""

    window.update_idletasks()

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    # Prevent dimensions from exceeding the screen
    width = min(width, screen_width)
    height = min(height, screen_height)

    x = (screen_width - width) // 2
    y = (screen_height - height) // 2

    window.geometry(f"{width}x{height}+{x}+{y}")
