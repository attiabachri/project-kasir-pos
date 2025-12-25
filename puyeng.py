import json
import tempfile
import platform
import subprocess
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import tkinter as tk
from tkinter import *
from tkinter import messagebox, simpledialog, filedialog, ttk
from PIL import Image, ImageTk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import csv
import os
from datetime import datetime, timedelta
import re


# File Database
USERS_DB = 'users.json'
PRODUCTS_DB = 'products.json'
TRANSACTIONS_DB = 'transactions.json'
LAPORAN_DB = 'laporan.json'
CONFIG_DB = 'config.json'
CUSTOMERS_DB = 'customers.json' # New database file for customers

# Tema Warna Professional
COLORS = {
    'primary': '#1e3a8a',  # Blue 900
    'secondary': '#3b82f6',  # Blue 500
    'success': '#10b981',  # Emerald 500
    'danger': '#ef4444',  # Red 500
    'warning': '#f59e0b',  # Amber 500
    'dark': '#1f2937',  # Gray 800
    'light': '#f9fafb',  # Gray 50
    'white': '#ffffff',
    'text_primary': '#111827',  # Gray 900
    'text_secondary': '#6b7280'  # Gray 500
}

# Load & Save Database
def load_db(filename):
    """Loads data from a JSON file. Initializes with default data if file is not found."""
    if not os.path.exists(filename):
        if filename in [TRANSACTIONS_DB, LAPORAN_DB]:
            return []
        elif filename == CONFIG_DB:
            return {
                'company': {
                    'name': 'PT PYRAMINDO SANTANA PUTRA',
                    'address': 'Jl. Raya Industri No. 123, Jakarta',
                    'phone': '+62-21-12345678',
                    'email': 'info@pyramindo.co.id',
                    'faximile': '031 - 3544193',
                    'logo': ''
                },
                'email': {
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'sender_email': '',
                    'sender_password': ''
                }
            }
        elif filename == CUSTOMERS_DB: # Default for customers DB
            return {}
        else:
            return {}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        messagebox.showwarning("Database Error", f"Error reading {filename}. It might be corrupted or not valid JSON. Using default empty data.")
        return {} if filename not in [TRANSACTIONS_DB, LAPORAN_DB] else []
    except FileNotFoundError: # This should ideally not be hit due to the os.path.exists check
        return {} if filename not in [TRANSACTIONS_DB, LAPORAN_DB] else []
    except Exception as e:
        messagebox.showerror("Database Error", f"An unexpected error occurred loading {filename}: {e}")
        return {} if filename not in [TRANSACTIONS_DB, LAPORAN_DB] else []

def save_db(data, filename):
    """Saves data to a JSON file."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        messagebox.showerror("Database Error", f"Could not save data to {filename}: {e}")

# Setup Initial Data
def setup_initial_data():
    """Initializes database files with default data if they don't exist."""
    if not os.path.exists(USERS_DB):
        save_db({
            'kasir': {'password': 'kasir123', 'role': 'kasir', 'email': 'kasir1@pyramindo.co.id'},
            'kasir1': {'password': 'kasir123', 'role': 'kasir', 'email': 'kasir1@pyramindo.co.id'},
            'kasir2': {'password': 'kasir456', 'role': 'kasir', 'email': 'kasir2@pyramindo.co.id'}
        }, USERS_DB)

    if not os.path.exists(PRODUCTS_DB):
        sample_products = {
            'P001': {
                'nama': 'Laptop Asus VivoBook',
                'harga': 8500000,
                'cc': 'Elektronik', # This is a category, not volume
                'Kapasitas Packaging': 'Box berisi 1 item',
            },
            'P002': {
                'nama': 'Mouse Wireless Logitech',
                'harga': 250000,
                'cc': 'Aksesoris', # This is a category, not volume
                'Kapasitas Packaging': 'Box berisi 1 item',
            },
            'P003': {
                'nama': 'Botol Kaca 500ml',
                'harga': 100000, # Harga per item
                'cc': '500cc', # This is volume
                'Kapasitas Packaging': 'Dus berisi 40 item', # 40 item per dus
            }
        }
        save_db(sample_products, PRODUCTS_DB)

    if not os.path.exists(CUSTOMERS_DB):
        save_db({}, CUSTOMERS_DB) # Initialize empty customers DB

# Email Functions
def send_invoice_email(invoice_data, customer_email, config):
    """Sends an invoice email to the customer."""
    try:
        smtp_config = config.get('email', {})
        if not smtp_config.get('sender_email') or not smtp_config.get('sender_password'):
            messagebox.showerror("Error", "Konfigurasi email belum diatur!")
            return False

        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_config['sender_email']
        msg['To'] = customer_email
        msg['Subject'] = f"Invoice #{invoice_data['invoice_id']} - {config.get('company', {}).get('name', 'Perusahaan Anda')}"

        html_content = generate_invoice_html(invoice_data, config)
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)

        server = smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'])
        server.starttls()
        server.login(smtp_config['sender_email'], smtp_config['sender_password'])
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengirim email: {str(e)}")
        return False

def generate_invoice_html(invoice_data, config):
    """Generates the HTML content for an invoice."""
    company = config.get('company', {})
    
    subtotal = invoice_data.get('subtotal', 0)
    tax_amount = invoice_data.get('tax_amount', 0)
    final_total = invoice_data.get('total', 0)

    items_html = ""
    for item in invoice_data.get('items', []):
        # In invoice, show the price per unit purchased (which is item['harga'] in cart)
        # And the quantity of *that unit* (item['qty_purchased_unit'] in cart)
        # So subtotal is correct.
        subtotal_item = item.get('harga', 0) * item.get('qty_purchased_unit', 0)
        items_html += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{item.get('nama', 'N/A')}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: center;">{item.get('qty_purchased_unit', 0)} ({item.get('unit_purchased', 'N/A')})</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">Rp {item.get('harga', 0):,}</td>
            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right;">Rp {subtotal_item:,}</td>
        </tr>
        """
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Invoice #{invoice_data.get('invoice_id', 'N/A')}</title>
</head>
<body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f9fafb;">
<div style="max-width: 800px; margin: 0 auto; background-color: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
<div style="background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 30px; border-radius: 8px 8px 0 0;">
<h1 style="margin: 0; font-size: 28px; font-weight: bold;">{company.get('name', 'Nama Perusahaan')}</h1>
<p style="margin: 10px 0 0 0; opacity: 0.9;">{company.get('address', 'Alamat Perusahaan')}</p>
<p style="margin: 5px 0 0 0; opacity: 0.9;">Tel: {company.get('phone', '-')}</p>
<p style="margin: 5px 0 0 0; opacity: 0.9;">Email: {company.get('email', '-')}</p>
</div>

<div style="padding: 30px;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 30px;">
        <div>
            <h2 style="color: #1e3a8a; margin: 0 0 10px 0;">INVOICE</h2>
            <p style="margin: 5px 0; color: #6b7280;">Invoice ID: <strong>#{invoice_data.get('invoice_id', 'N/A')}</strong></p>
            <p style="margin: 5px 0; color: #6b7280;">Nama Pelanggan: <strong>{invoice_data.get('customer_name', 'N/A')}</strong></p>
            <p style="margin: 5px 0; color: #6b7280;">Alamat Pelanggan: <strong>{invoice_data.get('customer_address', 'N/A')}</strong></p>
            <p style="margin: 5px 0; color: #6b7280;">Tanggal: <strong>{invoice_data.get('waktu', 'N/A')}</strong></p>
            <p style="margin: 5px 0; color: #6b7280;">Kasir: <strong>{invoice_data.get('kasir', 'N/A')}</strong></p>
        </div>
    </div>

    <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
        <thead>
            <tr style="background-color: #f3f4f6;">
                <th style="padding: 15px; text-align: left; border-bottom: 2px solid #e5e7eb;">Produk</th>
                <th style="padding: 15px; text-align: center; border-bottom: 2px solid #e5e7eb;">Qty</th>
                <th style="padding: 15px; text-align: right; border-bottom: 2px solid #e5e7eb;">Harga</th>
                <th style="padding: 15px; text-align: right; border-bottom: 2px solid #e5e7eb;">Subtotal</th>
            </tr>
        </thead>
        <tbody>
            {items_html}
        </tbody>
    </table>
    
    <div style="text-align: right; padding-right: 15px; margin-bottom: 15px;">
        <p style="margin: 5px 0; font-size: 14px; color: #6b7280;">Subtotal: Rp {subtotal:,}</p>
        <p style="margin: 5px 0; font-size: 14px; color: #6b7280;">Pajak ({invoice_data.get('tax_percentage', 0):.0f}%): Rp {tax_amount:,}</p>
    </div>

    <div style="text-align: right; margin-bottom: 30px;">
        <div style="background-color: #1e3a8a; color: white; padding: 20px; border-radius: 8px; display: inline-block;">
            <h3 style="margin: 0; font-size: 24px;">TOTAL: Rp {final_total:,}</h3>
        </div>
    </div>

    <div style="border-top: 1px solid #e5e7eb; padding-top: 20px; text-align: center; color: #6b7280;">
        <p>Terima kasih atas kepercayaan Anda!</p>
        <p style="font-size: 12px;">Invoice ini dibuat secara otomatis oleh sistem POS {company.get('name', 'Perusahaan Anda')}</p>
    </div>
</div>
</div>
</body>
</html>
"""

# MODIFIED PRINTING LOGIC
def generate_nota_string(nota_data, config):
    """Generates a plain text string for a sales receipt."""
    company = config.get('company', {})
    fax_line = f"Fax: {company['faximile']}" if company.get('faximile') else ""
    
    subtotal = nota_data.get('subtotal', 0)
    tax_amount = nota_data.get('tax_amount', 0)
    final_total = nota_data.get('total', 0)
    tax_percentage = nota_data.get('tax_percentage', 0)

    lines = [
        company.get('name', 'Nama Perusahaan'),
        company.get('address', 'Alamat Perusahaan'),
        f"Tel: {company.get('phone', '-')}",
    ]
    if fax_line:
        lines.append(fax_line)
    lines.extend([
        "="*50,
        "NOTA PENJUALAN",
        "="*50,
        f"Invoice ID: #{nota_data.get('invoice_id', 'N/A')}",
        f"Nama Pelanggan: {nota_data.get('customer_name', 'N/A')}",
        f"Alamat Pelanggan: {nota_data.get('customer_address', 'N/A')}",
        f"Tanggal        : {nota_data.get('waktu', 'N/A')}",
        f"Kasir          : {nota_data.get('kasir', 'N/A')}",
        "="*50
    ])

    item_lines = []
    for item in nota_data.get('items', []):
        subtotal_item = item.get('harga', 0) * item.get('qty_purchased_unit', 0)
        
        packaging_info = ""
        if item.get('unit_purchased') in ['dus', 'box'] and item.get('packaging_capacity', 1) > 1:
            packaging_info = f" ({item.get('packaging_capacity', 1)} item/dus)"
        elif item.get('unit_purchased') in ['dus', 'box'] and item.get('packaging_capacity', 1) == 1:
             packaging_info = f" (1 item/dus)"
        
        item_name = item.get('nama', 'N/A')
        full_qty_str = f"{item.get('qty_purchased_unit', 0)} {item.get('unit_purchased', 'N/A')}{packaging_info}"

        item_lines.append(f"{item_name:<25} {full_qty_str:<12} x Rp{item.get('harga', 0):>10,} = Rp{subtotal_item:>10,}")

    lines.extend(item_lines)
    lines.extend([
        "="*50,
        f"Subtotal       : Rp {subtotal:,}",
        f"Pajak ({tax_percentage:.0f}%)    : Rp {tax_amount:,}",
        "-"*50,
        f"TOTAL          : Rp {final_total:,}",
        "="*50,
        "Terima kasih atas kunjungan Anda!"
    ])
    return "\n".join(lines)

def show_print_preview_and_print_dialog(master_window, nota_content_str, config, app_colors):
    """Shows a print preview dialog and handles printing actions."""
    preview_dialog = Toplevel(master_window)
    preview_dialog.title("Pratinjau Nota & Opsi Cetak")
    dialog_width = 500
    dialog_height = 600
    preview_dialog.geometry(f"{dialog_width}x{dialog_height}")

    preview_dialog.configure(bg=app_colors['white'])
    preview_dialog.transient(master_window)
    preview_dialog.grab_set()

    master_x = master_window.winfo_rootx()
    master_y = master_window.winfo_rooty()
    master_width = master_window.winfo_width()
    master_height = master_window.winfo_height()
    x_pos = master_x + (master_width // 2) - (dialog_width // 2)
    y_pos = master_y + (master_height // 2) - (dialog_height // 2)
    preview_dialog.geometry(f'{dialog_width}x{dialog_height}+{x_pos}+{y_pos}')

    Label(preview_dialog, text="PRATINJAU NOTA",
          font=('Arial', 16, 'bold'),
          bg=app_colors['white'], fg=app_colors['primary']).pack(pady=10)

    text_area_frame = Frame(preview_dialog, bg=app_colors['white'], relief=SUNKEN, borderwidth=1)
    text_area_frame.pack(pady=10, padx=10, fill=BOTH, expand=True)

    text_area = Text(text_area_frame, wrap=WORD, font=('Courier New', 10), relief=FLAT, borderwidth=0,
                     bg=app_colors['white'], fg=app_colors['text_primary'])
    text_area.insert(END, nota_content_str)
    text_area.config(state=DISABLED)  # Make text area read-only

    scrollbar_y = Scrollbar(text_area_frame, orient=VERTICAL, command=text_area.yview)
    text_area.configure(yscrollcommand=scrollbar_y.set)
    scrollbar_y.pack(side=RIGHT, fill=Y)
    text_area.pack(side=LEFT, fill=BOTH, expand=True)

    btn_frame = Frame(preview_dialog, bg=app_colors['white'])
    btn_frame.pack(pady=20)

    def actual_print_action():
        tmpfile_path = None
        print_initiated_successfully = False
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w', encoding='utf-8', prefix='nota_') as tmpfile:
                tmpfile.write(nota_content_str)
                tmpfile_path = tmpfile.name

            current_os = platform.system()

            if current_os == "Windows":
                try:
                    os.startfile(tmpfile_path, "print")
                    messagebox.showinfo("Info Cetak",
                                        "Dialog cetak sistem telah dibuka.\nSilakan pilih printer Anda dan konfirmasi pencetakan.",
                                        parent=preview_dialog)
                    print_initiated_successfully = True
                except Exception as e_startfile:
                    try: # Fallback: open with default app for manual printing
                        os.startfile(tmpfile_path)
                        messagebox.showwarning("Info Cetak",
                                               f"Gagal membuka dialog cetak ({e_startfile}).\n"
                                               f"File nota ({os.path.basename(tmpfile_path)}) telah dibuka.\n"
                                               f"Silakan cetak secara manual (File > Print) dan pilih printer Anda.",
                                               parent=preview_dialog)
                        print_initiated_successfully = True  # Assume dialog is open and user will handle it
                    except Exception as e_open_fallback:
                        messagebox.showerror("Error Cetak",
                                             f"Gagal membuka dialog cetak atau file nota.\nError: {e_open_fallback}",
                                             parent=preview_dialog)

            elif current_os == "Darwin": # macOS
                try:
                    subprocess.run(['open', '-p', tmpfile_path], check=True, timeout=20) # Increased timeout
                    messagebox.showinfo("Info Cetak",
                                        "Dialog cetak akan muncul.\nSilakan pilih printer Anda dan konfirmasi pencetakan.",
                                        parent=preview_dialog)
                    print_initiated_successfully = True
                except subprocess.TimeoutExpired:
                    messagebox.showwarning("Info Cetak",
                                           "Proses cetak menunggu input Anda pada dialog cetak (timeout internal diabaikan).\n"
                                           "Jika dialog cetak terbuka, silakan lanjutkan dari sana.",
                                           parent=preview_dialog)
                    print_initiated_successfully = True # Assume dialog is open and user will handle it
                except Exception as e_mac:
                    messagebox.showerror("Error Cetak",
                                         f"Gagal memunculkan dialog cetak di macOS: {e_mac}",
                                         parent=preview_dialog)

            else: # Linux and other Unix-like
                try:
                    subprocess.Popen(['xdg-open', tmpfile_path])
                    messagebox.showinfo("Info Cetak",
                                         f"File nota ({os.path.basename(tmpfile_path)}) dibuka dengan aplikasi default.\n"
                                         f"Silakan gunakan menu File -> Print untuk memilih printer dan mencetak.",
                                         parent=preview_dialog)
                    print_initiated_successfully = True
                except Exception as e_xdg:
                    try:
                        subprocess.run(['lp', tmpfile_path], check=True, timeout=10)
                        messagebox.showwarning("Peringatan Cetak",
                                               f"Gagal membuka file dengan aplikasi default ({e_xdg}).\n"
                                               f"Mencoba mengirim nota ke printer default via 'lp'.",
                                               parent=preview_dialog)
                        print_initiated_successfully = True # Sent to default
                    except Exception as e_lp:
                        messagebox.showerror("Error Cetak",
                                             f"Gagal memproses cetak via xdg-open maupun lp.\nError lp: {e_lp}",
                                             parent=preview_dialog)

            if print_initiated_successfully:
                preview_dialog.destroy()  # Close the preview dialog if print action was initiated
        except Exception as e_outer:
            messagebox.showerror("Error Cetak Global", f"Terjadi kesalahan dalam proses persiapan cetak: {str(e_outer)}", parent=preview_dialog)
        finally:
            # Schedule the temporary file for deletion after a delay
            if tmpfile_path and os.path.exists(tmpfile_path):
                master_window.after(30000, lambda p=tmpfile_path: os.remove(p) if os.path.exists(p) else None)

    Button(btn_frame, text="🖨️ Cetak Nota",
           font=('Arial', 12, 'bold'),
           bg=app_colors['secondary'], fg=app_colors['white'],
           command=actual_print_action).pack(side=LEFT, padx=10, ipady=5)

    Button(btn_frame, text="❌ Batal",
           font=('Arial', 12, 'bold'),
           bg=app_colors['danger'], fg=app_colors['white'],
           command=preview_dialog.destroy).pack(side=LEFT, padx=10, ipady=5)

    preview_dialog.lift()
    preview_dialog.focus_force()
    preview_dialog.wait_window()

# Main Application Class
class ModernKasirApp:
    """Main application class for the POS system."""
    def __init__(self, master):
        self.master = master
        master.title("PT Pyramindo Santana Putra - Glass Bottle Manufacturing Industry")
        master.geometry("1200x800")
        master.configure(bg=COLORS['light'])
        master.state('zoomed')  # Maximize window on startup

        setup_initial_data()
        self.users = load_db(USERS_DB)
        self.products = load_db(PRODUCTS_DB)
        self.transactions = load_db(TRANSACTIONS_DB)
        self.customers = load_db(CUSTOMERS_DB) # Load customers data
        self.config = load_db(CONFIG_DB)

        self.logged_in_user = None
        self.logged_in_role = None
        self.cart = []
        self.current_tax_percentage = 0 # New: To store current tax percentage

        self.customer_for_transaction = None # To store selected customer for current transaction

        self.setup_styles()

        self.show_login()

    def setup_styles(self):
        """Configures ttk styles for consistent UI elements."""
        style = ttk.Style()
        style.theme_use('clam') # Use 'clam' theme for a modern look

        style.configure('Title.TLabel', font=('Arial', 24, 'bold'), background=COLORS['light'])
        style.configure('Heading.TLabel', font=('Arial', 16, 'bold'), background=COLORS['light'])
        style.configure('Modern.TButton', font=('Arial', 12, 'bold'), padding=(20, 10))
        style.configure('Card.TFrame', background=COLORS['white'], relief='raised', borderwidth=1)
        style.configure('DarkText.TLabel', foreground=COLORS['text_primary'], background=COLORS['white'], font=('Arial', 10))
        style.configure('BlueButton.TButton', background=COLORS['secondary'], foreground=COLORS['white'], font=('Arial', 12, 'bold'))
        style.map('BlueButton.TButton', background=[('active', COLORS['primary'])])
        style.configure('GreenButton.TButton', background=COLORS['success'], foreground=COLORS['white'], font=('Arial', 14, 'bold'))
        style.map('GreenButton.TButton', background=[('active', '#0e9e6e')])
        style.configure('RedButton.TButton', background=COLORS['danger'], foreground=COLORS['white'], font=('Arial', 14, 'bold'))
        style.map('RedButton.TButton', background=[('active', '#d03c3c')])


    def clear_screen(self):
        """Removes all widgets from the master window."""
        for widget in self.master.winfo_children():
            widget.destroy()

    def create_header(self, title, subtitle=""):
        """Creates a consistent header for different application screens."""
        header_frame = Frame(self.master, bg=COLORS['primary'], height=120)
        header_frame.pack(fill=X)
        header_frame.pack_propagate(False) # Prevent frame from shrinking to fit content

        title_label = Label(header_frame, text=title,
                            font=('Arial', 24, 'bold'),
                            bg=COLORS['primary'], fg=COLORS['white'])
        title_label.pack(pady=15)

        if subtitle:
            subtitle_label = Label(header_frame, text=subtitle,
                                   font=('Arial', 12),
                                   bg=COLORS['primary'], fg=COLORS['white'])
            subtitle_label.pack()

    def create_card(self, parent, title=""):
        """Creates a styled card-like frame with an optional title."""
        card_frame = ttk.Frame(parent, style='Card.TFrame')
        if title:
            title_label = Label(card_frame, text=title,
                                font=('Arial', 16, 'bold'),
                                bg=COLORS['white'], fg=COLORS['text_primary'])
            title_label.pack(pady=10)
        return card_frame

    def show_login(self):
        """Displays the user login screen."""
        self.clear_screen()

        main_frame = Frame(self.master, bg=COLORS['light'])
        main_frame.pack(fill=BOTH, expand=True)

        login_frame = Frame(main_frame, bg=COLORS['white'], relief='raised', borderwidth=2)
        login_frame.place(relx=0.5, rely=0.5, anchor=CENTER, width=400, height=350) # Centered login frame

        Label(login_frame, text="🏢", font=('Arial', 48), bg=COLORS['white']).pack(pady=20)
        Label(login_frame, text="SILAHKAN LOGIN",
              font=('Arial', 18, 'bold'),
              bg=COLORS['white'], fg=COLORS['primary']).pack()
        Label(login_frame, text="PT Pyramindo Santana Putra",
              font=('Arial', 12),
              bg=COLORS['white'], fg=COLORS['text_secondary']).pack(pady=(0, 20))

        form_frame = Frame(login_frame, bg=COLORS['white'])
        form_frame.pack(padx=40, fill=X)

        Label(form_frame, text="Username",
              font=('Arial', 12, 'bold'),
              bg=COLORS['white'], fg=COLORS['text_primary']).pack(anchor=W)
        self.username_entry = Entry(form_frame, font=('Arial', 12), relief='solid', borderwidth=1)
        self.username_entry.pack(fill=X, pady=(5, 15), ipady=8)

        Label(form_frame, text="Password",
              font=('Arial', 12, 'bold'),
              bg=COLORS['white'], fg=COLORS['text_primary']).pack(anchor=W)
        self.password_entry = Entry(form_frame, show='*', font=('Arial', 12), relief='solid', borderwidth=1)
        self.password_entry.pack(fill=X, pady=(5, 20), ipady=8)

        login_btn = Button(form_frame, text="LOGIN",
                           font=('Arial', 14, 'bold'),
                           bg=COLORS['primary'], fg=COLORS['white'],
                           relief='flat', borderwidth=0,
                           command=self.try_login)
        login_btn.pack(fill=X, ipady=12)

        self.master.bind('<Return>', lambda e: self.try_login()) # Bind Enter key to login

    def try_login(self):
        """Authenticates user login credentials."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if username in self.users and self.users[username].get('password') == password:
            self.logged_in_user = username
            self.logged_in_role = self.users[username].get('role')

            self.show_kasir_dashboard()
        else:
            messagebox.showerror("Login Gagal", "Username atau password salah!")

    def show_kasir_dashboard(self):
        """Displays the cashier dashboard with transaction and history options."""
        self.clear_screen()
        self.create_header("DASHBOARD KASIR", f"Selamat datang, {self.logged_in_user}")

        content_frame = Frame(self.master, bg=COLORS['light'])
        content_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        stats_frame = Frame(content_frame, bg=COLORS['light'])
        stats_frame.pack(fill=X, pady=(0, 20))

        my_transactions = [t for t in self.transactions if t.get('kasir') == self.logged_in_user]

        card1 = self.create_card(stats_frame, "Transaksi Hari Ini")
        card1.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))
        today_transactions = [t for t in my_transactions if t.get('waktu','').startswith(datetime.now().strftime('%Y-%m-%d'))]
        Label(card1, text=str(len(today_transactions)),
              font=('Arial', 32, 'bold'),
              bg=COLORS['white'], fg=COLORS['primary']).pack(pady=10)

        card2 = self.create_card(stats_frame, "Penjualan Hari Ini")
        card2.pack(side=LEFT, fill=BOTH, expand=True, padx=(10, 0))
        today_revenue = sum(t.get('total',0) for t in today_transactions)
        Label(card2, text=f"Rp {today_revenue:,}",
              font=('Arial', 24, 'bold'),
              bg=COLORS['white'], fg=COLORS['success']).pack(pady=10)

        menu_frame = Frame(content_frame, bg=COLORS['light'])
        menu_frame.pack(fill=BOTH, expand=True)

        buttons = [
            ("🛒 Transaksi Baru", self.show_transaction, COLORS['success']),
            ("📦 Kelola Produk", self.show_product_management, COLORS['secondary']),
            ("📊 Laporan Penjualan", self.show_sales_report, COLORS['success']),
            ("📋 Riwayat Transaksi", self.show_transactions, COLORS['secondary']),
            ("⚙️ Pengaturan", self.show_settings, COLORS['text_secondary']),
            ("👤 Kelola User", self.show_user_management, COLORS['primary']),
            ("👥 Kelola Pelanggan", self.show_customer_management, COLORS['primary']), # New button for customer management
            ("🚪 Logout", self.logout, COLORS['danger'])
        ]

        # Use grid to create a responsive, organized layout for all buttons
        for i, (text, command, color) in enumerate(buttons):
            row = i // 3
            col = i % 3
            btn = Button(menu_frame, text=text,
                            font=('Arial', 14, 'bold'),
                            bg=color, fg=COLORS['white'],
                            relief='flat', borderwidth=0,
                            command=command)
            btn.grid(row=row, column=col, padx=10, pady=10, sticky='nsew', ipadx=20, ipady=20)

        for i in range(3): # Configure grid weights for a responsive layout with 3 columns
            menu_frame.grid_columnconfigure(i, weight=1)
        num_rows = (len(buttons) + 2) // 3
        for i in range(num_rows): # Configure grid weights for rows
            menu_frame.grid_rowconfigure(i, weight=1)

    def show_transaction(self):
        """Displays the new transaction screen for cashiers."""
        self.clear_screen()
        
        # Header (Top Bar) - Changed background to primary color for elegance
        header_frame = Frame(self.master, bg=COLORS['primary'], height=80) # Increased height
        header_frame.pack(fill=X)
        header_frame.pack_propagate(False)

        # Title/Logo
        Label(header_frame, text="PT PYRAMINDO SANTANA PUTRA", font=('Arial', 20, 'bold'), fg=COLORS['white'], bg=COLORS['primary']).pack(side=LEFT, padx=20)
        
        # Top-right section for customer, date, transaction number, and cashier
        top_right_frame = Frame(header_frame, bg=COLORS['primary'])
        top_right_frame.pack(side=RIGHT, padx=10)

        # Customer Info
        customer_info_frame = Frame(top_right_frame, bg=COLORS['primary'])
        customer_info_frame.pack(side=LEFT, padx=10)
        Label(customer_info_frame, text="CUSTOMER:", font=('Arial', 10), fg=COLORS['light'], bg=COLORS['primary']).pack(anchor=W)
        self.customer_name_for_transaction_label = Label(customer_info_frame, text="CASH", font=('Arial', 14, 'bold'), fg=COLORS['white'], bg=COLORS['primary'])
        self.customer_name_for_transaction_label.pack(anchor=W)
        self.customer_address_for_transaction_label = Label(customer_info_frame, text="", font=('Arial', 10), fg=COLORS['light'], bg=COLORS['primary'])
        self.customer_address_for_transaction_label.pack(anchor=W)
        self.customer_email_for_transaction_label = Label(customer_info_frame, text="", font=('Arial', 10), fg=COLORS['light'], bg=COLORS['primary'])
        self.customer_email_for_transaction_label.pack(anchor=W)

        # Date & Sale No. & Cashier in a structured way
        details_frame = Frame(top_right_frame, bg=COLORS['primary'])
        details_frame.pack(side=RIGHT, padx=10, anchor=N) # Align to top

        # Date
        Label(details_frame, text="TANGGAL:", font=('Arial', 10), fg=COLORS['light'], bg=COLORS['primary']).grid(row=0, column=0, sticky=W)
        Label(details_frame, text=datetime.now().strftime('%d %b %Y'), font=('Arial', 14, 'bold'), fg=COLORS['white'], bg=COLORS['primary']).grid(row=1, column=0, sticky=W, pady=(0,5))

        # No. Penjualan (Transaction Number)
        Label(details_frame, text="NO. PENJUALAN:", font=('Arial', 10), fg=COLORS['light'], bg=COLORS['primary']).grid(row=0, column=1, sticky=W, padx=20)
        Label(details_frame, text="AUTO", font=('Arial', 14, 'bold'), fg=COLORS['white'], bg=COLORS['primary']).grid(row=1, column=1, sticky=W, padx=20, pady=(0,5))

        # Cashier Name
        Label(details_frame, text="KASIR:", font=('Arial', 10), fg=COLORS['light'], bg=COLORS['primary']).grid(row=0, column=2, sticky=W)
        Label(details_frame, text=self.logged_in_user.upper(), font=('Arial', 14, 'bold'), fg=COLORS['white'], bg=COLORS['primary']).grid(row=1, column=2, sticky=W)
        
        main_content_frame = Frame(self.master, bg=COLORS['light'])
        main_content_frame.pack(fill=BOTH, expand=True)

        # Left: Main content area (table and transaction details)
        left_main_frame = Frame(main_content_frame, bg=COLORS['light'])
        left_main_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=15, pady=15) # Increased padding

        # Cari Item (Search Bar) - top left
        cari_item_frame = Frame(left_main_frame, bg=COLORS['light'])
        cari_item_frame.pack(fill=X, pady=(0, 15)) # Increased padding
        Label(cari_item_frame, text="Cari Item :", font=('Arial', 14, 'bold'), bg=COLORS['light'], fg=COLORS['text_primary']).pack(side=LEFT, padx=(0, 10)) # Larger font, dark text
        self.item_search_entry = Entry(cari_item_frame, font=('Arial', 14), bd=2, relief='flat', highlightbackground=COLORS['secondary'], highlightthickness=1) # Thicker border, flat relief
        self.item_search_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 15), ipady=5) # Increased padding, internal padding
        self.item_search_entry.bind('<Return>', self.add_item_by_search_or_code) # Bind Enter to search/add
        
        # Product List Table (Central Top) - Now functions as the Cart Display
        product_list_frame = Frame(left_main_frame, bg=COLORS['white'], relief='flat', borderwidth=0) # Flat relief for modern look
        product_list_frame.pack(fill=BOTH, expand=True, pady=10)

        # Treeview Styles
        style = ttk.Style()
        style.configure("Treeview",
                        font=('Arial', 11),
                        rowheight=28, # Increased row height for better touch/click experience
                        fieldbackground=COLORS['white'],
                        background=COLORS['white'],
                        foreground=COLORS['text_primary'])
        style.configure("Treeview.Heading",
                        font=('Arial', 12, 'bold'),
                        background=COLORS['light'], # Lighter heading background
                        foreground=COLORS['primary'], # Primary color for heading text
                        relief='flat')
        style.map('Treeview.Heading',
                  background=[('active', COLORS['secondary'])]) # Hover effect for headings

        product_columns = ('No', 'ID Produk', 'Nama Item', 'Cc', 'Harga Satuan', 'Kapasitas Packaging') # 'Kode Item' changed to 'ID Produk'
        self.product_search_tree = ttk.Treeview(product_list_frame, columns=product_columns, show='headings', style="Treeview")
        for col in product_columns:
            self.product_search_tree.heading(col, text=col)
            self.product_search_tree.column(col, width=100, anchor=CENTER)
            if col == 'Nama Item': self.product_search_tree.column(col, width=200, anchor='center') # Centered item name column
            if col == 'Harga Satuan': self.product_search_tree.column(col, anchor='center', width=120) # Centered price column
            if col == 'Kapasitas Packaging': self.product_search_tree.column(col, width=150, anchor='center') # Wider column for packaging capacity

        vsb = ttk.Scrollbar(product_list_frame, orient="vertical", command=self.product_search_tree.yview)
        hsb = ttk.Scrollbar(product_list_frame, orient="horizontal", command=self.product_search_tree.xview)
        self.product_search_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.pack(side=RIGHT, fill=Y)
        hsb.pack(side=BOTTOM, fill=X)
        self.product_search_tree.pack(fill=BOTH, expand=True, padx=(5,0), pady=(5,0)) # Adjusted padding

        self.product_search_tree.bind('<<TreeviewSelect>>', self.on_product_select_for_transaction) # Select item via click
        self.item_search_entry.bind('<KeyRelease>', self.filter_products_for_transaction) # Live search in table

        # Detail Transaksi (Bottom Left) - Enhanced card look
        detail_transaksi_frame = Frame(left_main_frame, bg=COLORS['dark'], height=220, relief='flat', borderwidth=0) # Darker, flat relief, increased height
        detail_transaksi_frame.pack(fill=X, pady=15) # Increased padding
        detail_transaksi_frame.pack_propagate(False)
        
        Label(detail_transaksi_frame, text="DETAIL TRANSAKSI", font=('Arial', 16, 'bold'), bg=COLORS['dark'], fg=COLORS['white']).pack(pady=(15, 10)) # Larger font, more padding
        
        self.detail_labels = {}
        detail_fields = [
            ("Nama Pelanggan", "N/A"),
            ("Email Pelanggan", "N/A"),
            ("Subtotal", "N/A"),
            ("Pajak", "N/A"),
            ("Total Belanja", "N/A")
        ]
        
        for text, default_val in detail_fields:
            row_frame = Frame(detail_transaksi_frame, bg=COLORS['dark'])
            row_frame.pack(fill=X, padx=20, pady=2) # Increased padx
            Label(row_frame, text=f"{text}:", font=('Arial', 11), bg=COLORS['dark'], fg=COLORS['light'], width=18, anchor='w').pack(side=LEFT) # Lighter text, fixed width
            self.detail_labels[text] = Label(row_frame, text=default_val, font=('Arial', 11, 'bold'), bg=COLORS['dark'], fg=COLORS['white'], anchor='w')
            self.detail_labels[text].pack(side=LEFT, fill=X, expand=True)

        # Right Section (Buttons) - Modernized appearance
        right_buttons_frame = Frame(main_content_frame, bg=COLORS['light'])
        right_buttons_frame.pack(side=RIGHT, fill=Y, padx=15, pady=15) # Increased padding
        
        # Top 4 blue buttons
        ttk.Button(right_buttons_frame, text="DATA PELANGGAN", style='BlueButton.TButton', command=self.open_customer_selection).pack(fill=X, pady=8, ipady=12) # Increased padding
        ttk.Button(right_buttons_frame, text="RESET", style='BlueButton.TButton', command=self.reset_transaction).pack(fill=X, pady=8, ipady=12) # Changed from HARGA to RESET
        ttk.Button(right_buttons_frame, text="PAJAK", style='BlueButton.TButton', command=self.prompt_for_tax).pack(fill=X, pady=8, ipady=12)
        ttk.Button(right_buttons_frame, text="INPUT MANUAL", style='BlueButton.TButton', command=self.add_manual_item_to_transaction).pack(fill=X, pady=8, ipady=12)
        ttk.Button(right_buttons_frame, text="HAPUS ITEM", style='BlueButton.TButton', command=self.remove_item_from_cart).pack(fill=X, pady=8, ipady=12) # New button to remove item
        
        # Spacer
        Frame(right_buttons_frame, height=50, bg=COLORS['light']).pack(pady=10) # Adjust height as needed

        # Bottom 2 action buttons
        ttk.Button(right_buttons_frame, text="PROSES", style='GreenButton.TButton', command=self.process_transaction).pack(fill=X, pady=10, ipady=20) # Increased padding
        ttk.Button(right_buttons_frame, text="KEMBALI", style='RedButton.TButton', command=self.return_to_kasir_dashboard).pack(fill=X, pady=10, ipady=20)

        self.refresh_transaction_display() # Initialize detail display
        self.refresh_product_search_list() # Initial load of products for transaction

    def reset_transaction(self):
        """Resets the current transaction, clearing the cart and input fields."""
        if messagebox.askyesno("Konfirmasi Reset", "Apakah Anda yakin ingin mereset transaksi saat ini? Semua item di keranjang akan dihapus.", parent=self.master):
            self.cart = []
            self.customer_for_transaction = None # Reset selected customer
            self.current_tax_percentage = 0 # Reset tax
            self.item_search_entry.delete(0, END) # Clear search entry
            self.refresh_transaction_display() # Reset detail display
            self.refresh_product_search_list() # Reload product list
            messagebox.showinfo("Reset Berhasil", "Transaksi telah direset.", parent=self.master)


    def refresh_transaction_details_display(self):
        """DEPRECATED. No longer used."""
        pass
        
    def filter_products_for_transaction(self, event=None):
        """Filters the products displayed in the transaction Treeview based on search term."""
        for item_tree_id in self.product_search_tree.get_children():
            self.product_search_tree.delete(item_tree_id)
        
        term = self.item_search_entry.get().lower()
        if not term and not self.products: # If no search term and no products, just clear and return
            return

        displayed_count = 0
        for pid, prod in self.products.items():
            # Check if search term matches any relevant product field
            if not term or \
               term in pid.lower() or \
               term in prod.get('nama', '').lower() or \
               term in prod.get('cc', '').lower() or \
               term in prod.get('Kapasitas Packaging', '').lower():
                self.product_search_tree.insert('', 'end', values=(
                    displayed_count + 1, # Use a running number for 'No'
                    pid, # This is the product ID
                    prod.get('nama', 'N/A'), 
                    prod.get('cc', 'N/A'), 
                    f"Rp {prod.get('harga', 0):,}", # Display base item price
                    prod.get('Kapasitas Packaging', 'N/A')
                ))
                displayed_count += 1
            if displayed_count >= 50: # Limit display to, say, 50 items for performance
                break

    def refresh_product_search_list(self):
        """Refreshes the product list for selection in transaction screen."""
        self.filter_products_for_transaction() # Simply re-run the filter without a search term

    def add_item_by_search_or_code(self, event=None):
        """Attempts to add an item to the transaction.
        If a product is selected in the treeview, it adds that.
        If the entry has text, it tries to find by ID.
        """
        selected_item = self.product_search_tree.selection()
        if selected_item:
            item_values = self.product_search_tree.item(selected_item[0])['values']
            pid = item_values[1] # ID Produk
            product = self.products.get(pid)
            if product:
                self.prompt_for_quantity_and_add(pid, product) 
            return

        item_code = self.item_search_entry.get().strip()
        if item_code:
            product = self.products.get(item_code)
            if product:
                self.prompt_for_quantity_and_add(item_code, product) 
                self.item_search_entry.delete(0, END)
                return
            else:
                messagebox.showinfo("Produk Tidak Ditemukan", f"Produk dengan kode '{item_code}' tidak ditemukan.", parent=self.master)
                return
        else:
            pass


    def on_product_select_for_transaction(self, event):
        """Handles selection of a product from the search treeview."""
        selected_item = self.product_search_tree.selection()
        if selected_item:
            item_values = self.product_search_tree.item(selected_item[0])['values']
            pid = item_values[1] # ID Produk
            product = self.products.get(pid)
            if product:
                self.prompt_for_quantity_and_add(pid, product) 
            self.item_search_entry.delete(0, END) # Clear entry after selection
            self.refresh_product_search_list() # Clear selection in treeview and reload list to show all


    def prompt_for_quantity_and_add(self, product_id, product_to_add):
        """
        Prompts for quantity and unit for a selected product, then adds to cart.
        Calculates total quantity in base units (items) and price per purchased unit (item/dus).
        """
        unit_options = ['item']
        packaging_capacity_str = product_to_add.get('Kapasitas Packaging', '1 item').lower()
        packaging_capacity_num = 1
        
        # Extract numeric part from 'Kapasitas Packaging'
        
        match = re.search(r'(\d+)\s*item', packaging_capacity_str)
        if match:
            try:
                packaging_capacity_num = int(match.group(1))
                if 'dus' in packaging_capacity_str or 'box' in packaging_capacity_str:
                    unit_options.append('dus')
                    unit_options.append('box')
            except ValueError:
                pass # Fallback to 1 if conversion fails

        qty_dialog = Toplevel(self.master)
        qty_dialog.title(f"Tambah {product_to_add.get('nama','N/A')}")
        qty_dialog_width = 350
        qty_dialog_height = 280
        qty_dialog.geometry(f"{qty_dialog_width}x{qty_dialog_height}")
        qty_dialog.transient(self.master)
        qty_dialog.grab_set()

        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        x_pos = master_x + (master_width // 2) - (qty_dialog_width // 2)
        y_pos = master_y + (master_height // 2) - (qty_dialog_height // 2)
        qty_dialog.geometry(f'{qty_dialog_width}x{qty_dialog_height}+{x_pos}+{y_pos}')

        Label(qty_dialog, text=f"Produk: {product_to_add.get('nama','N/A')}", font=('Arial', 12, 'bold')).pack(pady=10)
        
        unit_frame = Frame(qty_dialog)
        unit_frame.pack(pady=5)
        Label(unit_frame, text="Satuan:").pack(side=LEFT)
        unit_var = StringVar(value='item')
        
        # Add Radiobuttons for each unit option
        for option in sorted(list(set(unit_options))): # Ensure unique and sorted options
            Radiobutton(unit_frame, text=option.capitalize(), variable=unit_var, value=option).pack(side=LEFT, padx=5)

        Label(qty_dialog, text="Jumlah:").pack(pady=(10,0))
        qty_entry = Entry(qty_dialog)
        qty_entry.pack(pady=(0,5))
        qty_entry.insert(0, 1)

        Label(qty_dialog, text="Harga per unit (Rp):").pack(pady=(10,0))
        price_entry = Entry(qty_dialog)
        price_entry.pack(pady=(0,5))
        # Default price based on selected unit
        def update_price_entry_default(*args):
            selected_unit_for_default = unit_var.get()
            base_price_per_item = product_to_add.get('harga', 0)
            if selected_unit_for_default in ['dus', 'box']:
                price_entry.delete(0, END)
                price_entry.insert(0, base_price_per_item * packaging_capacity_num)
            else:
                price_entry.delete(0, END)
                price_entry.insert(0, base_price_per_item)

        unit_var.trace_add('write', update_price_entry_default)
        update_price_entry_default() # Set initial default price

        def add_to_cart_confirm():
            try:
                qty_purchased = int(qty_entry.get())
                if qty_purchased <= 0:
                    raise ValueError("Jumlah harus angka positif.")
                price_per_purchased_unit = int(price_entry.get())
                if price_per_purchased_unit <= 0:
                    raise ValueError("Harga harus angka positif.")
            except ValueError as e:
                messagebox.showerror("Input Error", str(e), parent=qty_dialog)
                return

            selected_unit = unit_var.get()
            
            # Calculate total quantity in base items and price per purchased unit (item/dus)
            actual_qty_in_items = 0
            price_for_cart_item = 0 # This will be the price for one purchased unit (item or dus)

            if selected_unit in ['dus', 'box']:
                actual_qty_in_items = qty_purchased * packaging_capacity_num
                price_for_cart_item = price_per_purchased_unit # This is the price for one dus/box
            else: # 'item' or other single unit
                actual_qty_in_items = qty_purchased
                price_for_cart_item = price_per_purchased_unit # This is the price for one item
            
            # Check if item is already in cart, if so, update it
            existing_item_in_cart = next((item for item in self.cart if item['id'] == product_id), None)
            if existing_item_in_cart:
                existing_item_in_cart['qty_purchased_unit'] += qty_purchased # Add more of the purchased unit
                existing_item_in_cart['jumlah'] += actual_qty_in_items # Add to total items
                existing_item_in_cart['harga'] = price_for_cart_item # Update price per unit (if changed)
                existing_item_in_cart['unit_purchased'] = selected_unit # Update purchased unit
                existing_item_in_cart['packaging_capacity'] = packaging_capacity_num # Store for reference
            else:
                cart_item = {
                    'id': product_id,
                    'nama': product_to_add.get('nama','N/A'),
                    'harga': price_for_cart_item, # Price per unit that was purchased (e.g., price per dus)
                    'qty_purchased_unit': qty_purchased, # How many 'dus' or 'items' were bought
                    'unit_purchased': selected_unit, # 'dus' or 'item'
                    'jumlah': actual_qty_in_items, # Total quantity in base units (items)
                    'packaging_capacity': packaging_capacity_num, # How many items in one purchased unit
                    'cc': product_to_add.get('cc', 'N/A') # Ensure 'cc' is copied from product_to_add
                }
                self.cart.append(cart_item)
            
            self.refresh_transaction_display()
            qty_dialog.destroy()

        Button(qty_dialog, text="Tambahkan", command=add_to_cart_confirm, font=('Arial', 12), bg=COLORS['success'], fg=COLORS['white']).pack(pady=10)
        qty_dialog.wait_window()


    def generate_manual_product_id(self):
        """Generates a unique manual product ID (M001, M002, ...)."""
        # Filter existing product IDs to find manual ones
        manual_ids = [k for k in self.products.keys() if k.startswith('M') and len(k) > 1 and k[1:].isdigit()]
        
        if not manual_ids:
            return "M001"
        
        # Find the maximum current manual product ID and increment it
        max_id_num = 0
        for prod_id in manual_ids:
            try:
                num = int(prod_id[1:]) 
                if num > max_id_num:
                    max_id_num = num
            except ValueError:
                continue
        
        return f"M{(max_id_num + 1):03d}"

    def add_manual_item_to_transaction(self):
        """
        Allows cashier to manually input details for a new item (not from product database)
        and optionally link to an existing customer or create a new one.
        """
        # First, ask about customer data source
        customer_choice = messagebox.askyesno(
            "Pilih Pelanggan",
            "Apakah Anda ingin memilih pelanggan dari database yang sudah ada?\n\n"
            "Jika 'Ya', Anda akan memilih pelanggan dari daftar.\n"
            "Jika 'Tidak', Anda akan memasukkan data pelanggan baru atau membiarkannya 'Umum'.",
            parent=self.master
        )

        if customer_choice:
            # User wants to select an existing customer
            self.open_customer_selection()
            # If customer_for_transaction is still None after selection, they cancelled.
            # We can then decide to proceed with 'Umum' or return.
            if not self.customer_for_transaction:
                messagebox.showinfo("Info", "Tidak ada pelanggan yang dipilih. Transaksi akan menggunakan 'Pelanggan Umum'.", parent=self.master)
                self.customer_for_transaction = None # Ensure it's explicitly None if cancelled
                self.refresh_transaction_display() # Update display to "CASH"

        # Proceed with item input regardless of customer selection outcome
        dialog = Toplevel(self.master)
        dialog.title("Input Manual Item & Pelanggan")
        dialog_width = 650
        dialog_height = 800 # Increased height for new fields
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self.master)
        dialog.grab_set()

        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        x_pos = master_x + (master_width // 2) - (dialog_width // 2)
        y_pos = master_y + (master_height // 2) - (dialog_height // 2)
        dialog.geometry(f'{dialog_width}x{dialog_height}+{x_pos}+{y_pos}')

        # Item details
        Label(dialog, text="--- Detail Item ---", font=('Arial', 14, 'bold'), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(10,5))
        item_name_var = StringVar()
        item_cc_var = StringVar() # New: Cc for manual item
        item_qty_var = StringVar(value="1")
        item_price_per_item_var = StringVar() # Price per item
        item_unit_var = StringVar(value="item")
        item_per_packaging_var = StringVar(value="1") # New: Items per dus/box

        Label(dialog, text="Nama Item:", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
        Entry(dialog, textvariable=item_name_var, font=('Arial', 12)).pack(fill=X, padx=20, pady=5)

        # Corrected label to reflect "Cc" as 'capacity'
        Label(dialog, text="Kapasitas (Cc) / Kategori:", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
        Entry(dialog, textvariable=item_cc_var, font=('Arial', 12)).pack(fill=X, padx=20, pady=5)


        Label(dialog, text="Jumlah:", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
        Entry(dialog, textvariable=item_qty_var, font=('Arial', 12)).pack(fill=X, padx=20, pady=5)

        Label(dialog, text="Satuan:", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
        unit_combobox = ttk.Combobox(dialog, textvariable=item_unit_var, values=['item', 'dus', 'box', 'pcs', 'unit'], state='readonly', font=('Arial', 12))
        unit_combobox.pack(fill=X, padx=20, pady=5)

        # Dynamic field for items per packaging
        packaging_frame = Frame(dialog, bg=COLORS['white'])
        self.packaging_label = Label(packaging_frame, text="Jumlah Item per Dus/Box:", font=('Arial', 12, 'bold'), bg=COLORS['white'])
        self.packaging_entry = Entry(packaging_frame, textvariable=item_per_packaging_var, font=('Arial', 12))

        def update_packaging_visibility(*args):
            if item_unit_var.get() in ['dus', 'box']:
                packaging_frame.pack(fill=X, padx=20, pady=5)
                self.packaging_label.pack(side=LEFT, anchor='w')
                self.packaging_entry.pack(side=RIGHT, fill=X, expand=True)
            else:
                packaging_frame.pack_forget()
                self.packaging_label.pack_forget()
                self.packaging_entry.pack_forget()
                item_per_packaging_var.set("1") # Reset when not applicable
            update_calculated_price()

        def update_calculated_price(*args):
            try:
                price_per_item = int(item_price_per_item_var.get()) if item_price_per_item_var.get() else 0
                items_per_packaging = int(item_per_packaging_var.get()) if item_per_packaging_var.get() else 1
                if item_unit_var.get() in ['dus', 'box']:
                    calculated_price = price_per_item * items_per_packaging
                    calculated_price_label.config(text=f"Harga per {item_unit_var.get().capitalize()}: Rp {calculated_price:,}")
                else:
                    calculated_price_label.config(text="")
            except ValueError:
                calculated_price_label.config(text="Harga/Jumlah tidak valid")


        item_unit_var.trace_add('write', update_packaging_visibility)
        item_price_per_item_var.trace_add('write', update_calculated_price)
        item_per_packaging_var.trace_add('write', update_calculated_price)

        Label(dialog, text="Harga per item (Rp):", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
        Entry(dialog, textvariable=item_price_per_item_var, font=('Arial', 12)).pack(fill=X, padx=20, pady=5)
        
        calculated_price_label = Label(dialog, text="", font=('Arial', 10, 'italic'), bg=COLORS['white'], fg=COLORS['text_secondary'])
        calculated_price_label.pack(pady=(0, 10), padx=20, anchor='e')

        # Customer details (only show if not selected from existing or if choosing to save)
        customer_details_frame = Frame(dialog, bg=COLORS['white'])
        customer_details_frame.pack(fill=X, padx=10, pady=10)

        # Populate if a customer was chosen from the database
        customer_name_var = StringVar()
        customer_email_var = StringVar()
        customer_address_var = StringVar()
        save_customer_var = BooleanVar()

        if self.customer_for_transaction:
            customer_name_var.set(self.customer_for_transaction.get('nama', ''))
            customer_email_var.set(self.customer_for_transaction.get('email', ''))
            customer_address_var.set(self.customer_for_transaction.get('alamat', ''))
            # If chosen from existing, we don't allow saving it again, and fields are read-only
            Label(customer_details_frame, text="--- Pelanggan Terpilih ---", font=('Arial', 14, 'bold'), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(15,5))
            Label(customer_details_frame, text=f"Nama: {customer_name_var.get()}", bg=COLORS['white'], font=('Arial', 12)).pack(anchor=W, padx=10)
            Label(customer_details_frame, text=f"Email: {customer_email_var.get()}", bg=COLORS['white'], font=('Arial', 12)).pack(anchor=W, padx=10)
            Label(customer_details_frame, text=f"Alamat: {customer_address_var.get()}", bg=COLORS['white'], font=('Arial', 12)).pack(anchor=W, padx=10)
        else:
            # Allow manual input for customer if no existing one was chosen
            Label(customer_details_frame, text="--- Detail Pelanggan (Baru) ---", font=('Arial', 14, 'bold'), bg=COLORS['white'], fg=COLORS['primary']).pack(pady=(15,5))
            Label(customer_details_frame, text="Nama Pelanggan:", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
            Entry(customer_details_frame, textvariable=customer_name_var, font=('Arial', 12)).pack(fill=X, padx=20, pady=5)

            Label(customer_details_frame, text="Email Pelanggan:", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
            Entry(customer_details_frame, textvariable=customer_email_var, font=('Arial', 12)).pack(fill=X, padx=20, pady=5)

            Label(customer_details_frame, text="Alamat Pelanggan:", font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(pady=(5,0), padx=20, anchor='w')
            Entry(customer_details_frame, textvariable=customer_address_var, font=('Arial', 12)).pack(fill=X, padx=20, pady=5)

            Checkbutton(customer_details_frame, text="Simpan data pelanggan ini?", variable=save_customer_var,
                        font=('Arial', 10), bg=COLORS['white']).pack(pady=(10, 15), padx=20, anchor='w')


        def confirm_add_manual():
            # Get item details
            name = item_name_var.get().strip()
            # MODIFIED: Get 'cc' value directly from item_cc_var
            cc = item_cc_var.get().strip() 
            unit = item_unit_var.get().strip()
            packaging_capacity_num = int(item_per_packaging_var.get()) if item_per_packaging_var.get() else 1

            try:
                qty_purchased = int(item_qty_var.get())
                price_per_item_base = int(item_price_per_item_var.get()) # This is price per single item (base unit)
                if not name or qty_purchased <= 0 or price_per_item_base <= 0:
                    raise ValueError("Nama item, jumlah, dan harga per item harus valid dan positif!")
                if unit in ['dus', 'box'] and packaging_capacity_num <= 0:
                    raise ValueError("Jumlah item per dus/box harus positif!")
            except ValueError as e:
                messagebox.showerror("Error", str(e), parent=dialog)
                return
            
            # Generate a new manual product ID
            manual_product_id = self.generate_manual_product_id()

            # Calculate total quantity in base units (items) and price per purchased unit (item/dus)
            actual_qty_in_items = 0
            price_for_cart_item = 0 # This will be the price for one purchased unit (item or dus)

            if unit in ['dus', 'box']:
                actual_qty_in_items = qty_purchased * packaging_capacity_num
                price_for_cart_item = price_per_item_base * packaging_capacity_num # Price for one dus/box
            else: # 'item' or other single unit
                actual_qty_in_items = qty_purchased
                price_for_cart_item = price_per_item_base # Price for one item

            cart_item = {
                'id': manual_product_id, 
                'nama': name,
                'harga': price_for_cart_item, # Price per unit that was purchased (e.g., price per dus)
                'qty_purchased_unit': qty_purchased, # How many 'dus' or 'items' were bought
                'unit_purchased': unit, # 'dus' or 'item'
                'jumlah': actual_qty_in_items, # Total quantity in base units (items)
                'packaging_capacity': packaging_capacity_num, # How many items in one purchased unit
                'cc': cc  # MODIFIED: Ensure 'cc' is taken directly from the input field 'item_cc_var'
            }
            self.cart.append(cart_item)

            # --- PERBAIKAN DI SINI ---
            # Tambahkan item ke database products juga
            self.products[manual_product_id] = {
                'nama': name,
                'harga': price_per_item_base, # Simpan harga per item (harga dasar)
                'cc': cc,
                'Kapasitas Packaging': f"Dus berisi {packaging_capacity_num} item" if unit in ['dus', 'box'] else "1 item",
            }
            save_db(self.products, PRODUCTS_DB)
            # --- AKHIR PERBAIKAN ---

            # Get customer details (only if not already selected)
            if not self.customer_for_transaction:
                cust_name = customer_name_var.get().strip()
                cust_email = customer_email_var.get().strip()
                cust_address = customer_address_var.get().strip()

                if cust_name: # If customer name is provided, consider it as a specific customer
                    if save_customer_var.get():
                        # Save or update customer in database
                        customer_id = self.get_or_create_customer_id(cust_name, cust_email, cust_address)
                        self.customers[customer_id] = {
                            'nama': cust_name,
                            'alamat': cust_address,
                            'email': cust_email
                        }
                        save_db(self.customers, CUSTOMERS_DB)
                        messagebox.showinfo("Sukses", "Data pelanggan berhasil disimpan!", parent=dialog)
                    
                    # Set customer for current transaction
                    self.customer_for_transaction = {
                        'nama': cust_name,
                        'email': cust_email,
                        'alamat': cust_address
                    }
                else:
                    self.customer_for_transaction = None # Reset to no specific customer if name is empty


            self.refresh_transaction_display()
            dialog.destroy()

        Button(dialog, text="Tambahkan & Atur Pelanggan", command=confirm_add_manual, bg=COLORS['success'], fg=COLORS['white'], font=('Arial', 12, 'bold')).pack(pady=10)
        Button(dialog, text="Batal", command=dialog.destroy, bg=COLORS['danger'], fg=COLORS['white'], font=('Arial', 12, 'bold')).pack()

        # Initial visibility update
        update_packaging_visibility()
        update_calculated_price() # Initial price update

        dialog.wait_window()
        

    def open_customer_selection(self):
        """Displays a dialog to select a customer for the current transaction."""
        customer_selection_dialog = Toplevel(self.master)
        customer_selection_dialog.title("Pilih Pelanggan")
        customer_selection_dialog.configure(bg=COLORS['light'])
        customer_selection_dialog.transient(self.master)
        customer_selection_dialog.grab_set()

        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        
        dialog_width = 780
        dialog_height = 460
        
        x_pos = master_x + (master_width // 2) - (dialog_width // 2)
        y_pos = master_y + (master_height // 2) - (dialog_height // 2)
        customer_selection_dialog.geometry(f'{dialog_width}x{dialog_height}+{x_pos}+{y_pos}')

        search_frame = Frame(customer_selection_dialog, bg=COLORS['light'])
        search_frame.pack(fill=X, padx=10, pady=10)

        Label(search_frame, text="Cari Pelanggan:", bg=COLORS['light'], font=('Arial', 12, 'bold')).pack(side=LEFT, padx=(0, 5))
        search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=search_var, font=('Arial', 12))
        search_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        customers_treeview_columns = ('ID Pelanggan', 'Nama', 'Alamat', 'Email')
        customers_treeview = ttk.Treeview(customer_selection_dialog, columns=customers_treeview_columns, show='headings')

        for col in customers_treeview_columns:
            customers_treeview.heading(col, text=col)
            customers_treeview.column(col, width=100, anchor='w')
        customers_treeview.column('ID Pelanggan', anchor='center')

        customers_treeview.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        def filter_customers_search(event=None):
            for item_tree_id in customers_treeview.get_children():
                customers_treeview.delete(item_tree_id)
            
            term = search_var.get().lower()
            for cust_id, cust_data in self.customers.items():
                if term in cust_id.lower() or term in cust_data.get('nama', '').lower() or \
                   term in cust_data.get('alamat', '').lower() or term in cust_data.get('email', '').lower():
                    customers_treeview.insert('', 'end', values=(
                        cust_id, cust_data.get('nama', 'N/A'), cust_data.get('alamat', 'N/A'), cust_data.get('email', 'N/A')
                    ))
        
        search_entry.bind('<KeyRelease>', filter_customers_search)
        filter_customers_search() # Initial load

        def select_customer():
            selected_item = customers_treeview.selection()
            if not selected_item:
                messagebox.showerror("Error", "Pilih pelanggan terlebih dahulu!", parent=customer_selection_dialog)
                return

            item_values = customers_treeview.item(selected_item[0])['values']
            cust_id = item_values[0]
            
            self.customer_for_transaction = self.customers.get(cust_id)
            if self.customer_for_transaction:
                self.customer_name_for_transaction_label.config(text=self.customer_for_transaction.get('nama', 'CASH'))
                self.customer_address_for_transaction_label.config(text=self.customer_for_transaction.get('alamat', ''))
                self.customer_email_for_transaction_label.config(text=self.customer_for_transaction.get('email', ''))
                self.detail_labels["Nama Pelanggan"].config(text=self.customer_for_transaction.get('nama', 'N/A'))
                self.detail_labels["Email Pelanggan"].config(text=self.customer_for_transaction.get('email', 'N/A'))
                self.refresh_transaction_display() # Update main screen details
                self.refresh_product_search_list() # Reload product list

            customer_selection_dialog.destroy()

        button_frame = Frame(customer_selection_dialog, bg=COLORS['light'])
        button_frame.pack(pady=10)
        Button(button_frame, text="✅ Pilih Pelanggan", font=('Arial', 12, 'bold'), bg=COLORS['success'], fg=COLORS['white'], command=select_customer).pack(side=LEFT, padx=5)
        Button(button_frame, text="❌ Batal", font=('Arial', 12, 'bold'), bg=COLORS['danger'], fg=COLORS['white'], command=customer_selection_dialog.destroy).pack(side=LEFT, padx=5)
        customer_selection_dialog.wait_window()


    def change_selected_item_price(self):
        """Allows cashier to change the price of the currently selected item in the *product search table*."""
        selected_item_treeview = self.product_search_tree.focus()
        if not selected_item_treeview:
            messagebox.showwarning("Pilih Produk", "Pilih produk dari tabel di atas untuk mengubah harganya.", parent=self.master)
            return

        item_values = self.product_search_tree.item(selected_item_treeview)['values']
        pid = item_values[1] # ID Produk
        product = self.products.get(pid)

        if not product:
            messagebox.showerror("Error", "Produk tidak ditemukan dalam database.", parent=self.master)
            return

        current_price = product.get('harga', 0) # This is the base item price from DB
        
        try:
            new_price = simpledialog.askinteger("Ubah Harga Produk", f"Masukkan HARGA PER ITEM baru untuk '{product.get('nama','N/A')}' (saat ini Rp {current_price:,}):",
                                                initialvalue=current_price, minvalue=1, parent=self.master)
            if new_price is not None:
                product['harga'] = new_price # Update the base item price in DB
                save_db(self.products, PRODUCTS_DB) # Save updated price to database
                self.refresh_product_search_list() # Refresh the product list to show new base price
                messagebox.showinfo("Sukses", f"Harga PER ITEM '{product.get('nama','N/A')}' berhasil diubah menjadi Rp {new_price:,}.", parent=self.master)
        except ValueError:
            messagebox.showerror("Error", "Harga tidak valid! Harus berupa angka.", parent=self.master)
        except Exception as e:
            messagebox.showerror("Error", f"Terjadi kesalahan saat mengubah harga: {e}", parent=self.master)
            
    def remove_item_from_cart(self):
        """Removes the selected item from the cart."""
        selected_item_treeview = self.product_search_tree.focus()
        if not selected_item_treeview:
            messagebox.showwarning("Pilih Item", "Pilih item dari keranjang untuk dihapus.", parent=self.master)
            return
        
        # Get the index of the selected item in the treeview
        item_index = self.product_search_tree.index(selected_item_treeview)
        
        if messagebox.askyesno("Konfirmasi Hapus", "Apakah Anda yakin ingin menghapus item ini dari keranjang?", parent=self.master):
            # Remove the item from the cart list using the index
            del self.cart[item_index]
            self.refresh_transaction_display() # Refresh the display to show the updated cart

    def prompt_for_tax(self):
        """Prompts for tax percentage and updates display."""
        try:
            tax_input = simpledialog.askfloat("Input Pajak", "Masukkan persentase pajak (contoh: 10 untuk 10%):",
                                              initialvalue=self.current_tax_percentage, minvalue=0, parent=self.master)
            if tax_input is not None:
                self.current_tax_percentage = tax_input
                self.refresh_transaction_display()
                self.refresh_product_search_list() # Reload product list
        except ValueError:
            messagebox.showerror("Error", "Input pajak tidak valid. Harus berupa angka.", parent=self.master)

    def refresh_transaction_display(self):
        """Refreshes the product list (cart) and transaction details display."""
        # Clear existing items in the cart display Treeview
        for item_tree_id in self.product_search_tree.get_children():
            self.product_search_tree.delete(item_tree_id)

        total_subtotal = 0
        total_items_count_base_unit = 0 # Total quantity in base item units
        
        # Insert current cart items into the product search treeview
        for idx, item in enumerate(self.cart):
            # Calculate subtotal based on the purchased unit's price and quantity
            subtotal = item.get('harga', 0) * item.get('qty_purchased_unit', 0)
            total_subtotal += subtotal
            total_items_count_base_unit += item.get('jumlah', 0) # 'jumlah' is already in base items

            # MODIFIED: Logic to correctly display 'cc' from cart item
            item_cc_display = item.get('cc', 'N/A') # Directly use 'cc' from the cart item

            # Prepare packaging info for display in the "Kapasitas Packaging" column
            packaging_info_display = ""
            if item.get('unit_purchased') in ['dus', 'box'] and item.get('packaging_capacity', 1) > 1:
                packaging_info_display = f"Dus berisi {item.get('packaging_capacity', 1)} item"
            elif item.get('unit_purchased') in ['dus', 'box'] and item.get('packaging_capacity', 1) == 1:
                packaging_info_display = f"Dus berisi 1 item" 
            else: 
                packaging_info_display = f"1 {item.get('unit_purchased', 'item')}"


            self.product_search_tree.insert('', 'end', values=(
                idx + 1,
                item.get('id', 'N/A'),
                item.get('nama', 'N/A'),
                item_cc_display, # MODIFIED: Use the correct item_cc_display
                f"Rp {item.get('harga', 0):,}", # Display price per purchased unit
                packaging_info_display
            ))
        
        # Calculate final total with tax
        tax_amount = total_subtotal * (self.current_tax_percentage / 100)
        final_total = total_subtotal + tax_amount

        # Update Detail Transaksi
        self.detail_labels["Nama Pelanggan"].config(text=self.customer_for_transaction.get('nama', 'CASH') if self.customer_for_transaction else 'CASH')
        self.detail_labels["Email Pelanggan"].config(text=self.customer_for_transaction.get('email', 'N/A') if self.customer_for_transaction else 'N/A')
        
        self.detail_labels["Subtotal"].config(text=f"Rp {total_subtotal:,}")
        self.detail_labels["Pajak"].config(text=f"{self.current_tax_percentage:.0f}% (Rp {tax_amount:,})")
        self.detail_labels["Total Belanja"].config(text=f"Rp {final_total:,}")
        
        # Update header customer display
        if self.customer_for_transaction:
            self.customer_name_for_transaction_label.config(text=self.customer_for_transaction.get('nama', 'CASH'))
            self.customer_address_for_transaction_label.config(text=self.customer_for_transaction.get('alamat', ''))
            self.customer_email_for_transaction_label.config(text=self.customer_for_transaction.get('email', ''))
        else:
            self.customer_name_for_transaction_label.config(text="CASH")
            self.customer_address_for_transaction_label.config(text="")
            self.customer_email_for_transaction_label.config(text="")


    def process_transaction(self):
        """Processes the payment, updates stock, saves transaction, and shows success."""
        if not self.cart:
            messagebox.showerror("Error", "Nota kosong! Tambahkan item sebelum memproses transaksi.", parent=self.master)
            return

        total_subtotal = sum(item.get('harga',0) * item.get('qty_purchased_unit',0) for item in self.cart)
        tax_amount = total_subtotal * (self.current_tax_percentage / 100)
        final_total = total_subtotal + tax_amount

        now = datetime.now()
        invoice_id = f"INV{now.strftime('%Y%m%d%H%M%S')}"

        customer_name = self.customer_for_transaction.get('nama', 'Umum') if self.customer_for_transaction else 'Umum'
        customer_email = self.customer_for_transaction.get('email', '') if self.customer_for_transaction else ''
        customer_address = self.customer_for_transaction.get('alamat', '') if self.customer_for_transaction else ''

        # Save or update customer information if it was selected/inputted
        if self.customer_for_transaction and customer_name != 'Umum': 
            customer_id = self.get_or_create_customer_id(customer_name, customer_email, customer_address)
            self.customers[customer_id] = {
                'nama': customer_name,
                'alamat': customer_address,
                'email': customer_email
            }
            save_db(self.customers, CUSTOMERS_DB)

        transaction = {
            'invoice_id': invoice_id,
            'kasir': self.logged_in_user,
            'waktu': now.strftime('%Y-%m-%d %H:%M:%S'),
            'items': self.cart.copy(), # Copy cart to save its state at time of transaction
            'subtotal': total_subtotal,
            'tax_percentage': self.current_tax_percentage,
            'tax_amount': tax_amount,
            'total': final_total,
            'payment_method': "Cash", # Default to Cash, can be expanded later
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_address': customer_address
        }

        self.transactions.append(transaction)
        save_db(self.transactions, TRANSACTIONS_DB)

        self.show_transaction_success(transaction)


    def show_transaction_success(self, transaction):
        """Displays a success message after a transaction and offers print/email options."""
        success_dialog = Toplevel(self.master)
        success_dialog.title("Transaksi Berhasil")
        # --- PERBAIKAN DI SINI ---
        dialog_width = 400
        dialog_height = 450 # Increased height to ensure all content fits
        success_dialog.geometry(f"{dialog_width}x{dialog_height}")
        # --- AKHIR PERBAIKAN ---
        success_dialog.configure(bg=COLORS['white'])
        success_dialog.transient(self.master)
        success_dialog.grab_set()

        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        x_pos = master_x + (master_width // 2) - (dialog_width // 2)
        y_pos = master_y + (master_height // 2) - (dialog_height // 2)
        success_dialog.geometry(f'{dialog_width}x{dialog_height}+{x_pos}+{y_pos}')

        Label(success_dialog, text="✅", font=('Arial', 48), bg=COLORS['white']).pack(pady=20)
        Label(success_dialog, text="TRANSAKSI BERHASIL!",
                font=('Arial', 16, 'bold'),
                bg=COLORS['white'], fg=COLORS['success']).pack()

        Label(success_dialog, text=f"Invoice ID: {transaction.get('invoice_id','N/A')}",
                font=('Arial', 12),
                bg=COLORS['white']).pack(pady=5)
        Label(success_dialog, text=f"Total: Rp {transaction.get('total',0):,}",
                font=('Arial', 14, 'bold'),
                bg=COLORS['white'], fg=COLORS['primary']).pack(pady=5)

        btn_frame_success = Frame(success_dialog, bg=COLORS['white'])
        btn_frame_success.pack(pady=20)

        Button(btn_frame_success, text="🖨️ Cetak Nota",
                font=('Arial', 12, 'bold'),
                bg=COLORS['secondary'], fg=COLORS['white'],
                command=lambda: self.print_invoice(transaction)).pack(pady=5, fill=X)

        if transaction.get('customer_email'):
            Button(btn_frame_success, text="📧 Kirim Email",
                    font=('Arial', 12, 'bold'),
                    bg=COLORS['warning'], fg=COLORS['white'],
                    command=lambda: self.send_invoice_email_wrapper(transaction)).pack(pady=5, fill=X)

        Button(btn_frame_success, text="✅ Selesai",
                font=('Arial', 12, 'bold'),
                bg=COLORS['success'], fg=COLORS['white'],
                command=lambda: self.finish_current_transaction_and_return(success_dialog)).pack(pady=5, fill=X)

    def print_invoice(self, transaction):
        """Generates and displays print preview for an invoice."""
        nota_content_str = generate_nota_string(transaction, self.config)
        show_print_preview_and_print_dialog(self.master, nota_content_str, self.config, COLORS)

    def send_invoice_email_wrapper(self, transaction):
        """Wrapper to send invoice email with error handling."""
        if send_invoice_email(transaction, transaction.get('customer_email'), self.config):
            messagebox.showinfo("Sukses", "Invoice berhasil dikirim ke email!", parent=self.master)

    def finish_current_transaction_and_return(self, dialog):
        """Resets cart and returns to cashier dashboard after a transaction."""
        dialog.destroy()
        self.cart = []
        self.customer_for_transaction = None
        self.current_tax_percentage = 0
        self.show_kasir_dashboard()
        
    def return_to_kasir_dashboard(self):
        """Returns to the cashier dashboard without saving the current transaction."""
        if messagebox.askyesno("Konfirmasi", "Yakin ingin kembali ke Dashboard Kasir? Transaksi saat ini tidak akan disimpan.", parent=self.master):
            self.cart = []
            self.customer_for_transaction = None
            self.current_tax_percentage = 0
            self.show_kasir_dashboard()

#=============================================================================
#*** BLOK KODE MANAJEMEN PRODUK ***
#=============================================================================
    def show_product_management(self):
        """Displays the product management page for admin."""
        self.clear_screen()
        self.create_header("MANAJEMEN PRODUK", "Kelola data produk")

        main_frame = Frame(self.master, bg=COLORS['light'])
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        list_card = self.create_card(main_frame, "Daftar Produk")
        list_card.pack(fill=BOTH, expand=True)

        search_frame = Frame(list_card, bg=COLORS['white'])
        search_frame.pack(fill=X, padx=10, pady=10)

        Label(search_frame, text="Cari Produk:",
              bg=COLORS['white'], font=('Arial', 12, 'bold')).pack(anchor=W)
        self.product_search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=self.product_search_var, font=('Arial', 12))
        search_entry.pack(fill=X, pady=5)
        search_entry.bind('<KeyRelease>', self.filter_product_management)

        columns = ('id', 'nama', 'harga', 'cc', 'kapasitas_packaging')
        self.product_mgmt_tree = ttk.Treeview(list_card, columns=columns, show='headings')

        self.product_mgmt_tree.heading('id', text='ID Produk')
        self.product_mgmt_tree.heading('nama', text='Nama Produk')
        self.product_mgmt_tree.heading('harga', text='Harga Per Item') # Changed header for clarity
        self.product_mgmt_tree.heading('cc', text='Cc')
        self.product_mgmt_tree.heading('kapasitas_packaging', text='Kapasitas Packaging')

        self.product_mgmt_tree.column('id', width=100, anchor='center')
        self.product_mgmt_tree.column('nama', width=200, anchor='center') # Adjusted for better readability
        self.product_mgmt_tree.column('harga', width=120, anchor='center') # Right-align currency
        self.product_mgmt_tree.column('cc', width=100, anchor='center') # Left-align category
        self.product_mgmt_tree.column('kapasitas_packaging', width=150, anchor='center')

        self.product_mgmt_tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.product_mgmt_tree.bind('<Double-1>', self.trigger_edit_dialog)

        btn_frame_prod_mgmt = Frame(self.master, bg=COLORS['light'])
        btn_frame_prod_mgmt.pack(fill=X, padx=20, pady=10)

        Button(btn_frame_prod_mgmt, text="➕ Tambah Produk",
                font=('Arial', 12, 'bold'), bg=COLORS['success'], fg=COLORS['white'],
                command=self.add_product).pack(side=LEFT, padx=5)

        Button(btn_frame_prod_mgmt, text="✏️ Edit Produk",
                font=('Arial', 12, 'bold'), bg=COLORS['warning'], fg=COLORS['white'],
                command=self.trigger_edit_dialog).pack(side=LEFT, padx=5)

        Button(btn_frame_prod_mgmt, text="🗑️ Hapus Produk",
                font=('Arial', 12, 'bold'), bg=COLORS['danger'], fg=COLORS['white'],
                command=self.delete_product).pack(side=LEFT, padx=5)

        Button(btn_frame_prod_mgmt, text="🔙 Kembali",
                font=('Arial', 12, 'bold'), bg=COLORS['text_secondary'], fg=COLORS['white'],
                command=self.show_kasir_dashboard).pack(side=RIGHT, padx=5)

        self.refresh_product_management_list()

    def show_product_form_dialog(self, product_id=None):
        """Displays a dialog for adding or editing product details."""
        is_edit = product_id is not None
        dialog_title = "Edit Produk" if is_edit else "Tambah Produk Baru"

        dialog = Toplevel(self.master)
        dialog.title(dialog_title)
        dialog.geometry("500x350") # Adjusted height
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self.master)
        dialog.grab_set()

        form_container = Frame(dialog, bg=COLORS['white'])
        form_container.pack(fill=BOTH, expand=True, padx=20, pady=10)

        form_frame = Frame(form_container, bg=COLORS['white'])
        form_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        product_vars = {
            'id': StringVar(), 'nama': StringVar(), 'harga': StringVar(),
            'cc': StringVar(), 'Kapasitas Packaging': StringVar(), 
        }

        if is_edit:
            product = self.products[product_id]
            product_vars['id'].set(product_id)
            product_vars['nama'].set(product.get('nama', ''))
            product_vars['harga'].set(str(product.get('harga', 0))) # This is base item price
            product_vars['cc'].set(product.get('cc', ''))
            product_vars['Kapasitas Packaging'].set(product.get('Kapasitas Packaging', ''))

        fields = [
            ('ID Produk', 'id'), ('Nama Produk', 'nama'), ('Harga Per Item', 'harga'), 
            ('Cc (Kapasitas / Kategori)', 'cc'), # MODIFIED: Label for Cc field
            ('Kapasitas Packaging (e.g., "Dus berisi 40 item")', 'Kapasitas Packaging'), 
        ]

        for label_text, var_key in fields:
            Label(form_frame, text=f"{label_text}:", font=('Arial', 11, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5,0))
            entry = Entry(form_frame, textvariable=product_vars[var_key], font=('Arial', 11))
            entry.pack(fill=X, pady=(0,5))
            if var_key == 'id' and is_edit:
                entry.config(state='disabled')

        btn_frame = Frame(dialog, bg=COLORS['light'])
        btn_frame.pack(fill=X, padx=20, pady=10, side=BOTTOM)

        def save_action():
            try:
                pid = product_vars['id'].get().strip()
                if not pid:
                    messagebox.showerror("Error", "ID Produk harus diisi!", parent=dialog)
                    return

                if not is_edit and pid in self.products:
                    messagebox.showerror("Error", "ID Produk sudah ada!", parent=dialog)
                    return

                nama = product_vars['nama'].get().strip()
                if not nama:
                    messagebox.showerror("Error", "Nama produk harus diisi!", parent=dialog)
                    return

                harga = int(product_vars['harga'].get()) # This is price per item

                # NEW LOGIC FOR KAPASITAS PACKAGING
                packaging_input = product_vars['Kapasitas Packaging'].get().strip()
                packaging_output = self.process_packaging_input(packaging_input)
                # END NEW LOGIC

                product_data = {
                    'nama': nama, 'harga': harga,
                    'cc': product_vars['cc'].get().strip(), # MODIFIED: Ensure 'cc' is taken from input
                    'Kapasitas Packaging': packaging_output,
                }

                if is_edit:
                    self.products[pid].update(product_data)
                else:
                    self.products[pid] = product_data

                save_db(self.products, PRODUCTS_DB)
                self.refresh_product_management_list()
                messagebox.showinfo("Sukses", f"Produk berhasil {'diupdate' if is_edit else 'ditambahkan'}!", parent=self.master)
                dialog.destroy()

            except ValueError:
                messagebox.showerror("Error", "Harga harus berupa angka!", parent=dialog) 
            except Exception as e:
                messagebox.showerror("Error", f"Terjadi kesalahan: {e}", parent=dialog)

        Button(btn_frame, text="💾 Simpan", bg=COLORS['success'], fg=COLORS['white'], command=save_action).pack(side=LEFT)
        Button(btn_frame, text="❌ Batal", bg=COLORS['danger'], fg=COLORS['white'], command=dialog.destroy).pack(side=RIGHT)

        dialog.wait_window()
        
    def process_packaging_input(self, input_text):
        """
        Processes the input for 'Kapasitas Packaging'.
        If it's just a number or "number item", it formats it as "Dus berisi X item".
        Otherwise, it leaves the input as is.
        """
        # Remove any non-digit/non-word characters except for space
        cleaned_text = re.sub(r'[^\w\s]', '', input_text).strip()
        
        # Check if the cleaned input is a number followed by 'item'
        match_item = re.fullmatch(r'(\d+)\s*item', cleaned_text, re.IGNORECASE)
        if match_item:
            num = match_item.group(1)
            return f"Dus berisi {num} item"
        
        # Check if the cleaned input is just a number
        match_number = re.fullmatch(r'\d+', cleaned_text)
        if match_number:
            num = match_number.group(0)
            return f"Dus berisi {num} item"

        # If it doesn't match the simple formats, return the original text
        return input_text


    def trigger_edit_dialog(self, event=None):
        """Triggers the product form dialog for editing selected product."""
        selection = self.product_mgmt_tree.selection()
        if not selection:
            messagebox.showerror("Error", "Pilih produk yang akan diedit dari daftar!", parent=self.master)
            return

        selected_item = self.product_mgmt_tree.item(selection[0])
        product_id = selected_item['values'][0]
        self.show_product_form_dialog(product_id=product_id)

    def add_product(self):
        """Opens the product form dialog for adding a new product."""
        self.show_product_form_dialog()

    def edit_product(self):
        """Calls trigger_edit_dialog to edit a product (redundant but kept for clarity)."""
        self.trigger_edit_dialog()

    def delete_product(self):
        """Deletes the selected product from the database."""
        selection = self.product_mgmt_tree.selection()
        if not selection:
            messagebox.showerror("Error", "Pilih produk yang akan dihapus dari daftar!", parent=self.master)
            return

        selected_item = self.product_mgmt_tree.item(selection[0])
        pid = selected_item['values'][0]
        nama_produk = selected_item['values'][1]

        if messagebox.askyesno("Konfirmasi", f"Hapus produk {nama_produk}?", parent=self.master):
            del self.products[pid]
            save_db(self.products, PRODUCTS_DB)
            self.refresh_product_management_list()
            messagebox.showinfo("Sukses", "Produk berhasil dihapus!", parent=self.master)

    def filter_product_management(self, event=None):
        """Filters the products displayed in the product management Treeview."""
        search_term = self.product_search_var.get().lower()
        for item_tree_id in self.product_mgmt_tree.get_children():
            self.product_mgmt_tree.delete(item_tree_id)

        for pid, prod in sorted(self.products.items()):
            if search_term in prod.get('nama','').lower() or search_term in pid.lower() or \
               search_term in prod.get('cc','').lower() or search_term in prod.get('Kapasitas Packaging','').lower():
                self.product_mgmt_tree.insert('', 'end', values=(
                    pid,
                    prod.get('nama', 'N/A'),
                    f"Rp {prod.get('harga', 0):,}",
                    prod.get('cc', 'N/A'), # MODIFIED: Use the correct 'cc' value from product
                    prod.get('Kapasitas Packaging', 'N/A')
                ))

    def refresh_product_management_list(self):
        """Refreshes the list of products in the product management Treeview."""
        for item_tree_id in self.product_mgmt_tree.get_children():
            self.product_mgmt_tree.delete(item_tree_id)

        for pid, prod in sorted(self.products.items()):
            self.product_mgmt_tree.insert('', 'end', values=(
                pid,
                prod.get('nama', 'N/A'),
                f"Rp {prod.get('harga', 0):,}",
                prod.get('cc', 'N/A'), # MODIFIED: Use the correct 'cc' value from product
                prod.get('Kapasitas Packaging', 'N/A')
            ))
#=============================================================================
#*** AKHIR BLOK KODE MANAJEMEN PRODUK ***
#=============================================================================

    def show_transactions(self):
        """Displays the transaction history page."""
        self.clear_screen()
        self.create_header("RIWAYAT TRANSAKSI", "Daftar semua transaksi")

        main_frame = Frame(self.master, bg=COLORS['light'])
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        filter_frame = self.create_card(main_frame, "Filter Transaksi")
        filter_frame.pack(fill=X, pady=(0, 10))

        filter_content = Frame(filter_frame, bg=COLORS['white'])
        filter_content.pack(fill=X, padx=10, pady=10)

        # Search Input for transactions
        Label(filter_content, text="Cari Transaksi:",
              font=('Arial', 12, 'bold'),
              bg=COLORS['white']).pack(anchor=W)
        self.transaction_search_var = StringVar()
        search_entry = Entry(filter_content, textvariable=self.transaction_search_var, font=('Arial', 12))
        search_entry.pack(fill=X, pady=5)
        search_entry.bind('<KeyRelease>', self.filter_transactions_display)


        Label(filter_content, text="Filter Tanggal:",
                font=('Arial', 12, 'bold'),
                bg=COLORS['white']).pack(anchor=W, pady=(10,0))

        date_frame = Frame(filter_content, bg=COLORS['white'])
        date_frame.pack(fill=X, pady=5)

        self.date_filter_var = StringVar(value="Semua")
        Radiobutton(date_frame, text="Semua", variable=self.date_filter_var,
                    value="Semua", bg=COLORS['white'],
                    command=lambda: self.filter_transactions_display(None)).pack(side=LEFT)
        Radiobutton(date_frame, text="Hari Ini", variable=self.date_filter_var,
                    value="Hari Ini", bg=COLORS['white'],
                    command=lambda: self.filter_transactions_display(None)).pack(side=LEFT, padx=10)
        Radiobutton(date_frame, text="Minggu Ini", variable=self.date_filter_var,
                    value="Minggu Ini", bg=COLORS['white'],
                    command=lambda: self.filter_transactions_display(None)).pack(side=LEFT)

        list_frame = self.create_card(main_frame, "Daftar Transaksi")
        list_frame.pack(fill=BOTH, expand=True)

        # --- PERUBAHAN DI SINI ---
        columns = ('Invoice', 'Tanggal', 'Kasir', 'Pelanggan', 'Jumlah Keluar', 'Total')
        self.trans_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.trans_tree.heading(col, text=col)
            self.trans_tree.column(col, width=120, anchor=CENTER)
            if col == 'Invoice': self.trans_tree.column(col, width=150)
            if col == 'Tanggal': self.trans_tree.column(col, width=150)
            if col == 'Pelanggan': self.trans_tree.column(col, width=150)
            if col == 'Jumlah Keluar': self.trans_tree.column(col, width=150) # Kolom baru
        # --- AKHIR PERUBAHAN ---

        scrollbar = ttk.Scrollbar(list_frame, orient=VERTICAL, command=self.trans_tree.yview)
        self.trans_tree.configure(yscrollcommand=scrollbar.set)

        self.trans_tree.pack(side=LEFT, fill=BOTH, expand=True, padx=10, pady=10)
        scrollbar.pack(side=RIGHT, fill=Y, pady=10)

        self.trans_tree.bind('<<Double-1>>', self.show_transaction_detail_event)

        btn_frame_trans = Frame(self.master, bg=COLORS['light'])
        btn_frame_trans.pack(fill=X, padx=20, pady=10)

        Button(btn_frame_trans, text="📄 Detail Transaksi",
                font=('Arial', 12, 'bold'),
                bg=COLORS['secondary'], fg=COLORS['white'],
                command=self.show_selected_transaction_detail).pack(side=LEFT, padx=5)

        Button(btn_frame_trans, text="🔙 Kembali",
                font=('Arial', 12, 'bold'),
                bg=COLORS['text_secondary'], fg=COLORS['white'],
                command=self.show_kasir_dashboard).pack(side=RIGHT, padx=5)

        self.filter_transactions_display(None)

    def filter_transactions_display(self, event=None):
        """Filters and displays transactions in the history view based on date and search term."""
        for item_tree_id in self.trans_tree.get_children():
            self.trans_tree.delete(item_tree_id)

        filter_type = self.date_filter_var.get()
        search_term = self.transaction_search_var.get().lower()
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')

        for transaction in sorted(self.transactions, key=lambda t: t.get('waktu',''), reverse=True):
            trans_date_str = transaction.get('waktu','').split(' ')[0]

            # Date filter logic
            show_by_date = False
            if filter_type == "Semua":
                show_by_date = True
            elif filter_type == "Hari Ini" and trans_date_str == today_str:
                show_by_date = True
            elif filter_type == "Minggu Ini":
                try:
                    trans_dt = datetime.strptime(trans_date_str, '%Y-%m-%d')
                    if (now - trans_dt).days <= 6:
                        show_by_date = True
                except ValueError:
                    pass
            
            # Search filter logic
            show_by_search = False
            if not search_term: # If no search term, always show
                show_by_search = True
            else:
                # Concatenate relevant transaction details into a searchable string
                searchable_text = f"{transaction.get('invoice_id','').lower()} " \
                                  f"{transaction.get('kasir','').lower()} " \
                                  f"{transaction.get('customer_name','').lower()} " \
                                  f"{transaction.get('payment_method','').lower()} "
                
                # Also search in item names within the transaction
                for item in transaction.get('items', []):
                    searchable_text += f"{item.get('nama', '').lower()} "

                if search_term in searchable_text:
                    show_by_search = True

            if show_by_date and show_by_search:
                # --- PERUBAHAN DI SINI ---
                # Hitung total berdasarkan unit pembelian (dus, item, dll)
                unit_totals = {}
                for item in transaction.get('items', []):
                    unit = item.get('unit_purchased', 'item')
                    qty = item.get('qty_purchased_unit', 0)
                    unit_totals[unit] = unit_totals.get(unit, 0) + qty
                
                # Buat string ringkasan
                summary_str = " / ".join([f"{qty} {unit}" for unit, qty in unit_totals.items()])
                if not summary_str: summary_str = "0 item"

                self.trans_tree.insert('', 'end', values=(
                    transaction.get('invoice_id','N/A'),
                    transaction.get('waktu','N/A'),
                    transaction.get('kasir','N/A'),
                    transaction.get('customer_name', '-'),
                    summary_str, # Tampilkan ringkasan unit
                    f"Rp {transaction.get('total',0):,}"
                ))
                # --- AKHIR PERUBAHAN ---

    def show_transaction_detail_event(self, event):
        """Event handler for double-clicking a transaction in the history view."""
        self.show_selected_transaction_detail()

    def show_selected_transaction_detail(self,):
        """Displays details of the selected transaction from the history view."""
        selection = self.trans_tree.selection()
        if not selection:
            messagebox.showerror("Error", "Pilih transaksi terlebih dahulu!", parent=self.master)
            return

        item_values = self.trans_tree.item(selection[0])['values']
        invoice_id = item_values[0]

        transaction_data = next((trans for trans in self.transactions if trans.get('invoice_id') == invoice_id), None)

        if not transaction_data:
            messagebox.showerror("Error", "Transaksi tidak ditemukan!", parent=self.master)
            return

        self.show_transaction_detail_dialog(transaction_data)

    def show_transaction_detail_dialog(self, transaction):
        """Displays a detailed dialog for a specific transaction."""
        dialog = Toplevel(self.master)
        dialog.title(f"Detail Transaksi - {transaction.get('invoice_id','N/A')}")
        dialog_width = 600
        dialog_height = 700  # Increased height to fit all content
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.configure(bg=COLORS['white'])
        dialog.transient(self.master)
        dialog.grab_set()

        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        x_pos = master_x + (master_width // 2) - (dialog_width // 2)
        y_pos = master_y + (master_height // 2) - (dialog_height // 2)
        dialog.geometry(f'{dialog_width}x{dialog_height}+{x_pos}+{y_pos}')

        header_frame = Frame(dialog, bg=COLORS['primary'])
        header_frame.pack(fill=X)

        Label(header_frame, text="DETAIL TRANSAKSI",
                font=('Arial', 18, 'bold'),
                bg=COLORS['primary'], fg=COLORS['white']).pack(pady=10)

        info_frame = Frame(dialog, bg=COLORS['white'])
        info_frame.pack(fill=X, padx=20, pady=20)

        info_data = [
            ("Invoice ID", transaction.get('invoice_id','N/A')),
            ("Tanggal", transaction.get('waktu','N/A')),
            ("Kasir", transaction.get('kasir','N/A')),
            ("Metode Pembayaran", transaction.get('payment_method', 'Cash')),
            ("Nama Pelanggan", transaction.get('customer_name', '-')),
            ("Email Pelanggan", transaction.get('customer_email', '-')),
            ("Alamat Pelanggan", transaction.get('customer_address', '-')) # Added customer address
        ]

        for label, value in info_data:
            row_frame = Frame(info_frame, bg=COLORS['white'])
            row_frame.pack(fill=X, pady=2)

            Label(row_frame, text=f"{label}:",
                    font=('Arial', 11, 'bold'),
                    bg=COLORS['white'], width=20, anchor='w').pack(side=LEFT)
            Label(row_frame, text=str(value),
                    font=('Arial', 11),
                    bg=COLORS['white'], anchor='w').pack(side=LEFT, fill=X, expand=True)

        Label(dialog, text="ITEM PEMBELIAN",
                font=('Arial', 14, 'bold'),
                bg=COLORS['white']).pack(pady=(10, 5))

        items_frame = Frame(dialog, bg=COLORS['white'])
        items_frame.pack(fill=BOTH, expand=True, padx=20)

        columns_items = ('Nama', 'Qty', 'Harga', 'Subtotal', 'Cc') # MODIFIED: Added Cc to detail items
        items_tree = ttk.Treeview(items_frame, columns=columns_items, show='headings', height=5)

        for col in columns_items:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=100, anchor=CENTER)
            if col == 'Nama': items_tree.column(col, width=150, anchor='w') # Adjusted width
            if col == 'Qty': items_tree.column(col, width=80) # Adjusted width
            if col == 'Harga' or col == 'Subtotal' : items_tree.column(col, anchor='e')
            if col == 'Cc': items_tree.column(col, width=70, anchor='w') # Adjusted width for Cc

        for item_data in transaction.get('items',[]):
            subtotal = item_data.get('harga',0) * item_data.get('qty_purchased_unit',0)
            items_tree.insert('', 'end', values=(
                item_data.get('nama','N/A'),
                f"{item_data.get('qty_purchased_unit',0)} ({item_data.get('unit_purchased', 'N/A')})", 
                f"Rp {item_data.get('harga',0):,}", 
                f"Rp {subtotal:,}",
                item_data.get('cc', 'N/A') # MODIFIED: Include Cc value
            ))

        items_tree.pack(fill=BOTH, expand=True)

        total_frame = Frame(dialog, bg=COLORS['success'])
        total_frame.pack(fill=X, padx=20, pady=10)

        Label(total_frame, text=f"TOTAL: Rp {transaction.get('total',0):,}",
                font=('Arial', 16, 'bold'),
                bg=COLORS['success'], fg=COLORS['white']).pack(pady=10)

        btn_frame_detail = Frame(dialog, bg=COLORS['white'])
        btn_frame_detail.pack(pady=10)

        Button(btn_frame_detail, text="🖨️ Cetak Ulang",
                font=('Arial', 12, 'bold'),
                bg=COLORS['secondary'], fg=COLORS['white'],
                command=lambda: self.print_invoice(transaction)).pack(side=LEFT, padx=5)

        if transaction.get('customer_email'):
            Button(btn_frame_detail, text="📧 Kirim Email Ulang",
                    font=('Arial', 12, 'bold'),
                    bg=COLORS['warning'], fg=COLORS['white'],
                    command=lambda: self.send_invoice_email_wrapper(transaction)).pack(side=LEFT, padx=5)

        Button(btn_frame_detail, text="❌ Tutup",
                font=('Arial', 12, 'bold'),
                bg=COLORS['text_secondary'], fg=COLORS['white'],
                command=dialog.destroy).pack(side=LEFT, padx=5)
        dialog.grab_set()

    def show_sales_report(self):
        """Displays the sales report page with graphical representations."""
        self.clear_screen()
        self.create_header("LAPORAN PENJUALAN", "Analisis data penjualan")

        main_frame = Frame(self.master, bg=COLORS['light'])
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        control_frame = self.create_card(main_frame, "Pilih Jenis Laporan")
        control_frame.pack(fill=X, pady=(0, 10))

        control_content = Frame(control_frame, bg=COLORS['white'])
        control_content.pack(fill=X, padx=10, pady=10)

        self.report_type_var = StringVar(value="Harian")
        report_types = [("Harian", "Harian"), ("Mingguan", "Mingguan"), ("Bulanan", "Bulanan")]

        for text, value in report_types:
            Radiobutton(control_content, text=text, variable=self.report_type_var,
                        value=value, bg=COLORS['white'],
                        command=self.update_sales_report_display).pack(side=LEFT, padx=10)

        self.report_display_frame = self.create_card(main_frame, "Laporan Penjualan")
        self.report_display_frame.pack(fill=BOTH, expand=True)

        btn_frame_report = Frame(self.master, bg=COLORS['light'])
        btn_frame_report.pack(fill=X, padx=20, pady=10)

        Button(btn_frame_report, text="📊 Export ke CSV",
                font=('Arial', 12, 'bold'),
                bg=COLORS['success'], fg=COLORS['white'],
                command=self.export_report_to_csv).pack(side=LEFT, padx=5)

        Button(btn_frame_report, text="🔙 Kembali",
                font=('Arial', 12, 'bold'), bg=COLORS['text_secondary'], fg=COLORS['white'],
                command=self.show_kasir_dashboard).pack(side=RIGHT, padx=5)

        self.update_sales_report_display()

    def update_sales_report_display(self):
        """Updates the sales report display based on selected report type (daily, weekly, monthly)."""
        for widget in self.report_display_frame.winfo_children():
            if isinstance(widget, Label) and widget.cget('text') == "Laporan Penjualan":
                continue
            widget.destroy()

        report_type = self.report_type_var.get()

        try:
            if report_type == "Harian":
                self.generate_daily_report()
            elif report_type == "Mingguan":
                self.generate_weekly_report()
            elif report_type == "Bulanan":
                self.generate_monthly_report()
        except Exception as e:
            messagebox.showerror("Error Laporan", f"Terjadi kesalahan saat membuat laporan {report_type}: {e}\nPastikan data transaksi valid.", parent=self.master)
            Label(self.report_display_frame, text=f"Gagal memuat laporan {report_type}.\nDetail: {e}",
                    font=('Arial', 16), bg=COLORS['white'], fg=COLORS['danger']).pack(pady=50)

    def generate_daily_report(self):
        """Generates and displays a daily sales report chart."""
        daily_sales = {}
        for trans in self.transactions:
            date = trans.get('waktu','').split(' ')[0]
            if not date: continue
            daily_sales.setdefault(date, {'total': 0, 'count': 0})
            daily_sales[date]['total'] += trans.get('total',0)
            daily_sales[date]['count'] += 1

        if daily_sales:
            sorted_dates = sorted(daily_sales.keys())
            dates_to_plot = sorted_dates[-7:] # Show last 7 days with transactions
            totals = [daily_sales[date]['total'] for date in dates_to_plot]

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(dates_to_plot, totals, color=COLORS['primary'])
            ax.set_title('Penjualan Harian (Maks 7 Hari Terakhir dengan Transaksi)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Tanggal')
            ax.set_ylabel('Total Penjualan (Rp)')
            ax.tick_params(axis='x', rotation=45)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp {x:,.0f}'))
            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, self.report_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=BOTH, expand=True, padx=10, pady=10)

        else:
            Label(self.report_display_frame, text="Tidak ada data penjualan harian.",
                    font=('Arial', 16), bg=COLORS['white']).pack(pady=50)

    def generate_weekly_report(self):
        """Generates and displays a weekly sales report chart."""
        weekly_sales = {}
        for trans in self.transactions:
            date_str = trans.get('waktu','').split(' ')[0]
            if not date_str: continue
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                week_key = date_obj.strftime('%Y-W%U') # %U for week number (Sunday as first day)
                weekly_sales.setdefault(week_key, {'total': 0, 'count': 0, 'start_date': date_obj})
                weekly_sales[week_key]['total'] += trans.get('total',0)
                weekly_sales[week_key]['count'] += 1
            except ValueError:
                continue

        if weekly_sales:
            sorted_weeks = sorted(weekly_sales.keys(), key=lambda wk: weekly_sales[wk]['start_date'])
            weeks_to_plot = sorted_weeks[-4:] # Show last 4 weeks with transactions
            totals = [weekly_sales[week]['total'] for week in weeks_to_plot]

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.bar(weeks_to_plot, totals, color=COLORS['success'])
            ax.set_title('Penjualan Mingguan (Maks 4 Minggu Terakhir dengan Transaksi)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Minggu (Tahun-WMingguKe)')
            ax.set_ylabel('Total Penjualan (Rp)')
            ax.tick_params(axis='x', rotation=45)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp {x:,.0f}'))
            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, self.report_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=BOTH, expand=True, padx=10, pady=10)
        else:
            Label(self.report_display_frame, text="Tidak ada data penjualan mingguan.",
                    font=('Arial', 16), bg=COLORS['white']).pack(pady=50)

    def generate_monthly_report(self):
        """Generates and displays a monthly sales report chart."""
        monthly_sales = {}
        for trans in self.transactions:
            date_str = trans.get('waktu','')
            if not date_str or len(date_str) < 7: continue
            month_key = date_str[:7] #YYYY-MM
            monthly_sales.setdefault(month_key, {'total': 0, 'count': 0})
            monthly_sales[month_key]['total'] += trans.get('total',0)
            monthly_sales[month_key]['count'] += 1

        if monthly_sales:
            sorted_months = sorted(monthly_sales.keys())
            months_to_plot = sorted_months[-6:] # Show last 6 months with transactions
            totals = [monthly_sales[month]['total'] for month in months_to_plot]

            fig, ax = plt.subplots(figsize=(10, 5))
            ax.plot(months_to_plot, totals, marker='o', linewidth=2, markersize=6, color=COLORS['warning'])
            ax.set_title('Penjualan Bulanan (Maks 6 Bulan Terakhir dengan Transaksi)', fontsize=14, fontweight='bold')
            ax.set_xlabel('Bulan (Tahun-Bulan)')
            ax.set_ylabel('Total Penjualan (Rp)')
            ax.grid(True, linestyle='--', alpha=0.7)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'Rp {x:,.0f}'))
            plt.tight_layout()

            canvas = FigureCanvasTkAgg(fig, self.report_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=BOTH, expand=True, padx=10, pady=10)
        else:
            Label(self.report_display_frame, text="Tidak ada data penjualan bulanan.",
                    font=('Arial', 16), bg=COLORS['white']).pack(pady=50)

    def export_report_to_csv(self):
        """Exports all transaction data to a CSV file."""
        try:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Simpan Laporan Transaksi sebagai CSV",
                parent=self.master
            )
            if not filepath:
                return

            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Invoice ID', 'Tanggal', 'Kasir', 'Total', 'Metode Pembayaran', 'Nama Pelanggan', 'Email Pelanggan', 'Alamat Pelanggan', 'Item Dibeli'])

                for trans in self.transactions:
                    items_str_list = []
                    for item in trans.get('items',[]):
                        items_str_list.append(f"{item.get('nama','N/A')} (Qty Purchased: {item.get('qty_purchased_unit',0)} {item.get('unit_purchased', 'item')}, Price Per Unit Purchased: {item.get('harga',0)}, Total Base Items: {item.get('jumlah',0)})")
                    items_purchased_str = "; ".join(items_str_list)

                    writer.writerow([
                        trans.get('invoice_id','N/A'),
                        trans.get('waktu','N/A'),
                        trans.get('kasir','N/A'),
                        trans.get('total',0),
                        trans.get('payment_method', 'Cash'),
                        trans.get('customer_name', '-'),
                        trans.get('customer_email', '-'),
                        trans.get('customer_address', '-'), 
                        items_purchased_str
                    ])

            messagebox.showinfo("Sukses", f"Laporan berhasil diekspor ke {filepath}", parent=self.master)

        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengekspor laporan: {str(e)}", parent=self.master)

    def show_user_management(self):
        """Displays the user management page for admin to add, edit, or delete users."""
        self.clear_screen()
        self.create_header("MANAJEMEN USER", "Kelola data pengguna")

        main_frame = Frame(self.master, bg=COLORS['light'])
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        left_frame = self.create_card(main_frame, "Daftar User")
        left_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        self.user_mgmt_listbox = Listbox(left_frame, font=('Arial', 12))
        self.user_mgmt_listbox.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.user_mgmt_listbox.bind('<<ListboxSelect>>', self.load_user_details_form)

        right_frame = self.create_card(main_frame, "Detail User")
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(10, 0))

        form_frame_user = Frame(right_frame, bg=COLORS['white'])
        form_frame_user.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.user_form_vars = {
            'username': StringVar(), 'password': StringVar(),
            'role': StringVar(), 'email': StringVar()
        }

        Label(form_frame_user, text="Username:",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.username_form_entry = Entry(form_frame_user, textvariable=self.user_form_vars['username'], font=('Arial', 12))
        self.username_form_entry.pack(fill=X, pady=(0, 10))

        Label(form_frame_user, text="Password:",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.password_form_entry = Entry(form_frame_user, textvariable=self.user_form_vars['password'], show='*', font=('Arial', 12))
        self.password_form_entry.pack(fill=X, pady=(0, 10))

        Label(form_frame_user, text="Role:",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.role_form_combo = ttk.Combobox(form_frame_user, textvariable=self.user_form_vars['role'],
                                            values=['kasir'], state='readonly', font=('Arial', 11))
        self.role_form_combo.pack(fill=X, pady=(0, 10))

        Label(form_frame_user, text="Email:",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.email_form_entry = Entry(form_frame_user, textvariable=self.user_form_vars['email'], font=('Arial', 12))
        self.email_form_entry.pack(fill=X, pady=(0, 10))

        btn_frame_user_mgmt = Frame(self.master, bg=COLORS['light'])
        btn_frame_user_mgmt.pack(fill=X, padx=20, pady=10)

        Button(btn_frame_user_mgmt, text="➕ Tambah User",
                font=('Arial', 12, 'bold'), bg=COLORS['success'], fg=COLORS['white'],
                command=self.add_new_user).pack(side=LEFT, padx=5)
        Button(btn_frame_user_mgmt, text="✏️ Edit User",
                font=('Arial', 12, 'bold'), bg=COLORS['warning'], fg=COLORS['white'],
                command=self.edit_existing_user).pack(side=LEFT, padx=5)
        Button(btn_frame_user_mgmt, text="🗑️ Hapus User",
                font=('Arial', 12, 'bold'), bg=COLORS['danger'], fg=COLORS['white'],
                command=self.delete_selected_user).pack(side=LEFT, padx=5)
        Button(btn_frame_user_mgmt, text="🧹 Bersihkan Form",
                font=('Arial', 12, 'bold'), bg=COLORS['dark'], fg=COLORS['white'],
                command=self.clear_user_form_fields).pack(side=LEFT, padx=5)
        Button(btn_frame_user_mgmt, text="🔙 Kembali",
                font=('Arial', 12, 'bold'), bg=COLORS['text_secondary'], fg=COLORS['white'],
                command=self.show_kasir_dashboard).pack(side=RIGHT, padx=5)

        self.refresh_user_management_list()

    def refresh_user_management_list(self):
        """Refreshes the list of users in the user management view."""
        self.user_mgmt_listbox.delete(0, END)
        for username, user_data in self.users.items():
            self.user_mgmt_listbox.insert(END, f"{username} ({user_data.get('role','N/A')})")
        self.clear_user_form_fields() # Ensure form is reset after refresh

    def clear_user_form_fields(self):
        """Clears the input fields in the user management form and enables username entry."""
        self.user_form_vars['username'].set("")
        self.username_form_entry.config(state='normal') # Enable username entry for new user
        self.user_form_vars['password'].set("")
        self.user_form_vars['role'].set("")
        self.user_form_vars['email'].set("")
        self.user_mgmt_listbox.selection_clear(0, END) # Deselect any selected item

    def load_user_details_form(self, event):
        """Loads the details of the selected user into the form fields."""
        selection = self.user_mgmt_listbox.curselection()
        if not selection:
            self.clear_user_form_fields()
            return

        selected_text = self.user_mgmt_listbox.get(selection[0])
        username = selected_text.split(' (')[0]

        if username not in self.users:
            messagebox.showwarning("Peringatan", f"User {username} tidak ditemukan lagi.", parent=self.master)
            self.refresh_user_management_list()
            return

        user_data = self.users[username]

        self.user_form_vars['username'].set(username)
        self.username_form_entry.config(state='disabled') # Prevent changing username for existing user
        self.user_form_vars['password'].set(user_data.get('password',''))
        self.user_form_vars['role'].set(user_data.get('role',''))
        self.user_form_vars['email'].set(user_data.get('email', ''))

    def add_new_user(self):
        """Adds a new user to the system."""
        username = self.user_form_vars['username'].get().strip()
        password = self.user_form_vars['password'].get().strip()
        role = 'kasir' # Role is now hardcoded to kasir
        email = self.user_form_vars['email'].get().strip()

        if not username or not password:
            messagebox.showerror("Error", "Username dan password harus diisi!", parent=self.master)
            return

        if username in self.users:
            messagebox.showerror("Error", "Username sudah ada!", parent=self.master)
            return

        self.users[username] = {'password': password, 'role': role, 'email': email}
        save_db(self.users, USERS_DB)
        messagebox.showinfo("Sukses", "User berhasil ditambahkan!", parent=self.master)
        self.refresh_user_management_list() # Refresh list and clear form

    def edit_existing_user(self):
        """Edits the details of an existing user."""
        username = self.user_form_vars['username'].get().strip()

        if not username or username not in self.users:
            messagebox.showerror("Error", "Pilih user dari daftar untuk diedit atau user tidak valid.", parent=self.master)
            return

        password = self.user_form_vars['password'].get().strip()
        role = 'kasir' # Role is now hardcoded to kasir
        email = self.user_form_vars['email'].get().strip()

        if not password:
            messagebox.showerror("Error", "Password harus diisi!", parent=self.master)
            return

        self.users[username].update({'password': password, 'role': role, 'email': email})
        save_db(self.users, USERS_DB)
        messagebox.showinfo("Sukses", "User berhasil diupdate!", parent=self.master)
        self.refresh_user_management_list() # Refresh list and clear form

    def delete_selected_user(self):
        """Deletes the selected user from the system."""
        username = self.user_form_vars['username'].get().strip()
        if not username or username not in self.users:
            messagebox.showerror("Error", "Pilih user dari daftar untuk dihapus atau user tidak valid.", parent=self.master)
            return

        if username == self.logged_in_user:
            messagebox.showerror("Error", "Tidak dapat menghapus user yang sedang login!", parent=self.master)
            return

        if messagebox.askyesno("Konfirmasi", f"Hapus user {username}?", parent=self.master):
            del self.users[username]
            save_db(self.users, USERS_DB)
            messagebox.showinfo("Sukses", "User berhasil dihapus!", parent=self.master)
            self.refresh_user_management_list() # Refresh list and clear form

    def show_settings(self):
        """Displays the application settings page for company and email configurations."""
        self.clear_screen()
        self.create_header("PENGATURAN SISTEM", "Konfigurasi aplikasi")

        main_frame = Frame(self.master, bg=COLORS['light'])
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        # Ensure config dictionary has the necessary keys
        if 'company' not in self.config: self.config['company'] = {}
        if 'email' not in self.config: self.config['email'] = {}

        company_frame = self.create_card(main_frame, "Informasi Perusahaan")
        company_frame.pack(fill=X, pady=(0, 10))
        comp_content = Frame(company_frame, bg=COLORS['white'])
        comp_content.pack(fill=X, padx=10, pady=10)

        self.company_form_vars = {}
        company_fields = [
            ('Nama Perusahaan', 'name'), ('Alamat', 'address'),
            ('Telepon', 'phone'), ('Email Perusahaan', 'email'), ('Faximile', 'faximile'),
        ]
        for label_text, key in company_fields:
            Label(comp_content, text=f"{label_text}:",
                    font=('Arial', 11, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
            var = StringVar(value=self.config.get('company',{}).get(key, ''))
            self.company_form_vars[key] = var
            Entry(comp_content, textvariable=var, font=('Arial', 11)).pack(fill=X, pady=(0, 5))

        email_settings_frame = self.create_card(main_frame, "Pengaturan Email Notifikasi")
        email_settings_frame.pack(fill=X, pady=(0, 10))
        email_content = Frame(email_settings_frame, bg=COLORS['white'])
        email_content.pack(fill=X, padx=10, pady=10)

        self.email_settings_vars = {}
        email_fields = [
            ('SMTP Server', 'smtp_server'), ('SMTP Port', 'smtp_port'),
            ('Email Pengirim (untuk notifikasi)', 'sender_email'), ('Password Email Pengirim', 'sender_password')
        ]
        for label_text, key in email_fields:
            Label(email_content, text=f"{label_text}:",
                    font=('Arial', 11, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
            var = StringVar(value=str(self.config.get('email',{}).get(key, '')))
            self.email_settings_vars[key] = var
            entry_show = '*' if key == 'sender_password' else None
            Entry(email_content, textvariable=var, show=entry_show, font=('Arial', 11)).pack(fill=X, pady=(0, 5))

        btn_frame_settings = Frame(self.master, bg=COLORS['light'])
        btn_frame_settings.pack(fill=X, padx=20, pady=10)
        Button(btn_frame_settings, text="💾 Simpan Pengaturan",
                font=('Arial', 12, 'bold'), bg=COLORS['success'], fg=COLORS['white'],
                command=self.save_app_settings).pack(side=LEFT, padx=5)
        Button(btn_frame_settings, text="📧 Test Email",
                font=('Arial', 12, 'bold'), bg=COLORS['warning'], fg=COLORS['white'],
                command=self.test_email_configuration).pack(side=LEFT, padx=5)
        Button(btn_frame_settings, text="🔙 Kembali",
                font=('Arial', 12, 'bold'), bg=COLORS['text_secondary'], fg=COLORS['white'],
                command=self.show_kasir_dashboard).pack(side=RIGHT, padx=5)

    def save_app_settings(self):
        """Saves the application settings to the config file."""
        try:
            for key, var in self.company_form_vars.items():
                self.config['company'][key] = var.get().strip()

            for key, var in self.email_settings_vars.items():
                value = var.get().strip()
                if key == 'smtp_port':
                    value = int(value) if value else 587 # Default to 587 if empty
                self.config['email'][key] = value
            save_db(self.config, CONFIG_DB)
            messagebox.showinfo("Sukses", "Pengaturan berhasil disimpan!", parent=self.master)
        except ValueError:
            messagebox.showerror("Error", "Port SMTP harus berupa angka!", parent=self.master)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan pengaturan: {str(e)}", parent=self.master)

    def test_email_configuration(self):
        """Tests the configured email settings by attempting a connection."""
        try:
            smtp_config_test = {
                'smtp_server': self.email_settings_vars['smtp_server'].get().strip(),
                'smtp_port': int(self.email_settings_vars['smtp_port'].get().strip() or 587),
                'sender_email': self.email_settings_vars['sender_email'].get().strip(),
                'sender_password': self.email_settings_vars['sender_password'].get().strip()
            }

            if not all(smtp_config_test.values()):
                messagebox.showerror("Error", "Semua field email (server, port, email, password) harus diisi untuk tes!", parent=self.master)
                return

            server = smtplib.SMTP(smtp_config_test['smtp_server'], smtp_config_test['smtp_port'])
            server.starttls() # Enable TLS encryption
            server.login(smtp_config_test['sender_email'], smtp_config_test['sender_password'])
            server.quit()
            messagebox.showinfo("Sukses", "Koneksi email berhasil!", parent=self.master)
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menghubungkan ke server email: {str(e)}", parent=self.master)

    def logout(self):
        """Logs out the current user and returns to the login screen."""
        if messagebox.askyesno("Konfirmasi", "Yakin ingin logout?", parent=self.master):
            self.logged_in_user = None
            self.logged_in_role = None
            self.cart = []
            self.show_login()

    # New Customer Management Functions
    def show_customer_management(self):
        """Displays the customer management page for admin."""
        self.clear_screen()
        self.create_header("MANAJEMEN PELANGGAN", "Kelola data pelanggan")

        main_frame = Frame(self.master, bg=COLORS['light'])
        main_frame.pack(fill=BOTH, expand=True, padx=20, pady=20)

        list_card = self.create_card(main_frame, "Daftar Pelanggan")
        list_card.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 10))

        columns = ('ID Pelanggan', 'Nama', 'Alamat', 'Email')
        self.customer_mgmt_tree = ttk.Treeview(list_card, columns=columns, show='headings')

        self.customer_mgmt_tree.heading('ID Pelanggan', text='ID Pelanggan')
        self.customer_mgmt_tree.heading('Nama', text='Nama')
        self.customer_mgmt_tree.heading('Alamat', text='Alamat')
        self.customer_mgmt_tree.heading('Email', text='Email')

        self.customer_mgmt_tree.column('ID Pelanggan', width=100, anchor='center')
        self.customer_mgmt_tree.column('Nama', width=150, anchor='w')
        self.customer_mgmt_tree.column('Alamat', width=200, anchor='w')
        self.customer_mgmt_tree.column('Email', width=150, anchor='w')

        self.customer_mgmt_tree.pack(fill=BOTH, expand=True, padx=10, pady=10)
        self.customer_mgmt_tree.bind('<<TreeviewSelect>>', self.load_customer_details_to_form)

        right_frame = self.create_card(main_frame, "Detail Pelanggan")
        right_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(10, 0))

        form_frame_customer = Frame(right_frame, bg=COLORS['white'])
        form_frame_customer.pack(fill=BOTH, expand=True, padx=10, pady=10)

        self.customer_form_vars = {
            'id': StringVar(), 'nama': StringVar(), 'alamat': StringVar(), 'email': StringVar()
        }

        Label(form_frame_customer, text="ID Pelanggan (Otomatis):",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.customer_id_entry = Entry(form_frame_customer, textvariable=self.customer_form_vars['id'], font=('Arial', 12), state='disabled')
        self.customer_id_entry.pack(fill=X, pady=(0, 10))

        Label(form_frame_customer, text="Nama:",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.customer_name_form_entry = Entry(form_frame_customer, textvariable=self.customer_form_vars['nama'], font=('Arial', 12))
        self.customer_name_form_entry.pack(fill=X, pady=(0, 10))

        Label(form_frame_customer, text="Alamat:",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.customer_address_form_entry = Entry(form_frame_customer, textvariable=self.customer_form_vars['alamat'], font=('Arial', 12))
        self.customer_address_form_entry.pack(fill=X, pady=(0, 10))

        Label(form_frame_customer, text="Email:",
                font=('Arial', 12, 'bold'), bg=COLORS['white']).pack(anchor=W, pady=(5, 0))
        self.customer_email_form_entry = Entry(form_frame_customer, textvariable=self.customer_form_vars['email'], font=('Arial', 12))
        self.customer_email_form_entry.pack(fill=X, pady=(0, 10))

        btn_frame_customer_mgmt = Frame(self.master, bg=COLORS['light'])
        btn_frame_customer_mgmt.pack(fill=X, padx=20, pady=10)

        Button(btn_frame_customer_mgmt, text="➕ Tambah Pelanggan",
                font=('Arial', 12, 'bold'), bg=COLORS['success'], fg=COLORS['white'],
                command=self.add_new_customer).pack(side=LEFT, padx=5)
        Button(btn_frame_customer_mgmt, text="✏️ Edit Pelanggan",
                font=('Arial', 12, 'bold'), bg=COLORS['warning'], fg=COLORS['white'],
                command=self.edit_existing_customer_data).pack(side=LEFT, padx=5)
        Button(btn_frame_customer_mgmt, text="🗑️ Hapus Pelanggan",
                font=('Arial', 12, 'bold'), bg=COLORS['danger'], fg=COLORS['white'],
                command=self.delete_selected_customer).pack(side=LEFT, padx=5)
        Button(btn_frame_customer_mgmt, text="🧹 Bersihkan Form",
                font=('Arial', 12, 'bold'), bg=COLORS['dark'], fg=COLORS['white'],
                command=self.clear_customer_form_fields).pack(side=LEFT, padx=5)
        Button(btn_frame_customer_mgmt, text="🔙 Kembali",
                font=('Arial', 12, 'bold'), bg=COLORS['text_secondary'], fg=COLORS['white'],
                command=self.show_kasir_dashboard).pack(side=RIGHT, padx=5)

        self.refresh_customer_management_list()

    def generate_customer_id(self):
        """Generates a unique customer ID."""
        if not self.customers:
            return "C001"
        
        # Find the maximum current customer ID and increment it
        max_id_num = 0
        for cust_id in self.customers.keys():
            try:
                num = int(cust_id[1:]) # Assuming format CXXX
                if num > max_id_num:
                    max_id_num = num
            except ValueError:
                continue
        
        return f"C{(max_id_num + 1):03d}"

    def refresh_customer_management_list(self):
        """Refreshes the list of customers in the customer management Treeview."""
        for item_tree_id in self.customer_mgmt_tree.get_children():
            self.customer_mgmt_tree.delete(item_tree_id)
        
        for cust_id, cust_data in sorted(self.customers.items()):
            self.customer_mgmt_tree.insert('', 'end', values=(
                cust_id,
                cust_data.get('nama', 'N/A'),
                cust_data.get('alamat', 'N/A'),
                cust_data.get('email', 'N/A')
            ))
        self.clear_customer_form_fields()
        
    def clear_customer_form_fields(self):
        """Clears the input fields in the customer management form."""
        self.customer_form_vars['id'].set("")
        self.customer_name_form_entry.config(state='normal') # Enable name entry for new customer
        self.customer_form_vars['nama'].set("")
        self.customer_form_vars['alamat'].set("")
        self.customer_form_vars['email'].set("")
        self.customer_mgmt_tree.selection_remove(self.customer_mgmt_tree.selection())
    
    def load_customer_details_to_form(self, event):
        """Loads the details of the selected customer into the form fields."""
        selection = self.customer_mgmt_tree.selection()
        if not selection:
            self.clear_customer_form_fields()
            return
        
        selected_item = self.customer_mgmt_tree.item(selection[0])
        cust_id = selected_item['values'][0]

        if cust_id not in self.customers:
            messagebox.showwarning("Peringatan", f"Pelanggan {cust_id} tidak ditemukan lagi.", parent=self.master)
            self.refresh_customer_management_list()
            return

        customer_data = self.customers[cust_id]
        
        self.customer_form_vars['id'].set(cust_id)
        self.customer_name_form_entry.config(state='disabled') # Prevent changing name for existing customer
        self.customer_form_vars['nama'].set(customer_data.get('nama', ''))
        self.customer_form_vars['alamat'].set(customer_data.get('alamat', ''))
        self.customer_form_vars['email'].set(customer_data.get('email', ''))

    def add_new_customer(self):
        """Adds a new customer to the system."""
        nama = self.customer_form_vars['nama'].get().strip()
        alamat = self.customer_form_vars['alamat'].get().strip()
        email = self.customer_form_vars['email'].get().strip()

        if not nama:
            messagebox.showerror("Error", "Nama pelanggan harus diisi!", parent=self.master)
            return

        # Check for existing customer by name (simple check, could be improved)
        for cust_id, cust_data in self.customers.items():
            if cust_data.get('nama', '').lower() == nama.lower():
                messagebox.showerror("Error", "Pelanggan dengan nama tersebut sudah ada!", parent=self.master)
                return

        new_customer_id = self.generate_customer_id()
        self.customers[new_customer_id] = {
            'nama': nama,
            'alamat': alamat,
            'email': email
        }
        save_db(self.customers, CUSTOMERS_DB)
        self.refresh_customer_management_list()
        messagebox.showinfo("Sukses", "Pelanggan berhasil ditambahkan!", parent=self.master)

    def edit_existing_customer_data(self):
        """Edits the details of an existing customer."""
        cust_id = self.customer_form_vars['id'].get().strip()
        nama = self.customer_form_vars['nama'].get().strip() 
        alamat = self.customer_form_vars['alamat'].get().strip()
        email = self.customer_form_vars['email'].get().strip()

        if not cust_id or cust_id not in self.customers:
            messagebox.showerror("Error", "Pilih pelanggan dari daftar untuk diedit atau ID pelanggan tidak valid.", parent=self.master)
            return

        if not nama:
            messagebox.showerror("Error", "Nama pelanggan harus diisi!", parent=self.master)
            return
        
        self.customers[cust_id].update({
            'nama': nama,
            'alamat': alamat,
            'email': email
        })
        save_db(self.customers, CUSTOMERS_DB)
        self.refresh_customer_management_list()
        messagebox.showinfo("Sukses", "Data pelanggan berhasil diupdate!", parent=self.master)

    def delete_selected_customer(self):
        """Deletes the selected customer from the system."""
        cust_id = self.customer_form_vars['id'].get().strip()
        if not cust_id or cust_id not in self.customers:
            messagebox.showerror("Error", "Pilih pelanggan dari daftar untuk dihapus atau ID pelanggan tidak valid.", parent=self.master)
            return

        nama_pelanggan = self.customers[cust_id].get('nama', 'N/A')

        if messagebox.askyesno("Konfirmasi", f"Hapus pelanggan {nama_pelanggan} (ID: {cust_id})?", parent=self.master):
            del self.customers[cust_id]
            save_db(self.customers, CUSTOMERS_DB)
            self.refresh_customer_management_list()
            messagebox.showinfo("Sukses", "Pelanggan berhasil dihapus!", parent=self.master)

    def get_or_create_customer_id(self, name, email, address):
        """Finds an existing customer ID or generates a new one."""
        for cust_id, cust_data in self.customers.items():
            if cust_data.get('nama', '').lower() == name.lower() and \
               cust_data.get('email', '').lower() == email.lower() and \
               cust_data.get('alamat', '').lower() == address.lower():
                return cust_id
        return self.generate_customer_id()

    def choose_customer_for_transaction(self):
        """Displays a dialog to choose an existing customer for the current transaction."""
        customer_selection_dialog = Toplevel(self.master)
        customer_selection_dialog.title("Pilih Pelanggan")
        customer_selection_dialog.configure(bg=COLORS['light'])
        customer_selection_dialog.transient(self.master)
        customer_selection_dialog.grab_set()

        master_x = self.master.winfo_rootx()
        master_y = self.master.winfo_rooty()
        master_width = self.master.winfo_width()
        master_height = self.master.winfo_height()
        
        dialog_width = 600
        dialog_height = 400
        
        x_pos = master_x + (master_width // 2) - (dialog_width // 2)
        y_pos = master_y + (master_height // 2) - (dialog_height // 2)
        customer_selection_dialog.geometry(f'{dialog_width}x{dialog_height}+{x_pos}+{y_pos}')

        search_frame = Frame(customer_selection_dialog, bg=COLORS['light'])
        search_frame.pack(fill=X, padx=10, pady=10)

        Label(search_frame, text="Cari Pelanggan:", bg=COLORS['light'], font=('Arial', 12, 'bold')).pack(side=LEFT, padx=(0, 5))
        search_var = StringVar()
        search_entry = Entry(search_frame, textvariable=search_var, font=('Arial', 12))
        search_entry.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        
        customers_treeview_columns = ('ID Pelanggan', 'Nama', 'Alamat', 'Email')
        customers_treeview = ttk.Treeview(customer_selection_dialog, columns=customers_treeview_columns, show='headings')

        for col in customers_treeview_columns:
            customers_treeview.heading(col, text=col)
            customers_treeview.column(col, width=100, anchor='w')
        customers_treeview.column('ID Pelanggan', anchor='center')

        customers_treeview.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        def filter_customers_search(event=None):
            for item_tree_id in customers_treeview.get_children():
                customers_treeview.delete(item_tree_id)
            
            term = search_var.get().lower()
            for cust_id, cust_data in self.customers.items():
                if term in cust_id.lower() or term in cust_data.get('nama', '').lower() or \
                   term in cust_data.get('alamat', '').lower() or term in cust_data.get('email', '').lower():
                    customers_treeview.insert('', 'end', values=(
                        cust_id, cust_data.get('nama', 'N/A'), cust_data.get('alamat', 'N/A'), cust_data.get('email', 'N/A')
                    ))
        
        search_entry.bind('<KeyRelease>', filter_customers_search)
        filter_customers_search() # Initial load

        def select_customer():
            selected_item = customers_treeview.selection()
            if not selected_item:
                messagebox.showerror("Error", "Pilih pelanggan terlebih dahulu!", parent=customer_selection_dialog)
                return

            item_values = customers_treeview.item(selected_item[0])['values']
            cust_id = item_values[0]
            
            self.customer_for_transaction = self.customers.get(cust_id)
            if self.customer_for_transaction:
                self.customer_name_for_transaction_label.config(text=self.customer_for_transaction.get('nama', 'CASH'))
                self.customer_address_for_transaction_label.config(text=self.customer_for_transaction.get('alamat', ''))
                self.customer_email_for_transaction_label.config(text=self.customer_for_transaction.get('email', ''))
                self.detail_labels["Nama Pelanggan"].config(text=self.customer_for_transaction.get('nama', 'N/A'))
                self.detail_labels["Email Pelanggan"].config(text=self.customer_for_transaction.get('email', 'N/A'))
                self.refresh_transaction_display() # Update main screen details

            customer_selection_dialog.destroy()

        button_frame = Frame(customer_selection_dialog, bg=COLORS['light'])
        button_frame.pack(pady=10)
        Button(button_frame, text="✅ Pilih Pelanggan", font=('Arial', 12, 'bold'), bg=COLORS['success'], fg=COLORS['white'], command=select_customer).pack(side=LEFT, padx=5)
        Button(button_frame, text="❌ Batal", font=('Arial', 12, 'bold'), bg=COLORS['danger'], fg=COLORS['white'], command=customer_selection_dialog.destroy).pack(side=LEFT, padx=5)
        customer_selection_dialog.wait_window()


# Main execution
if __name__ == "__main__":
    root = tk.Tk()
    app = ModernKasirApp(root)
    root.mainloop()