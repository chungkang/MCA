import tkinter as tk
from tkinter import messagebox

# Tkinter Window
root = tk.Tk()
root.withdraw()  # hide default window

# popup message
messagebox.showinfo("title-test", "contents test.")

# Tkinter start event
root.mainloop()
