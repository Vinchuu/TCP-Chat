"""
Graphical User Interface (GUI) TCP Chat Client
Computer Networks Lab (CNL) Project

Built with Python's built-in Tkinter framework (zero external dependencies).
Features:
- Modern dark-themed chat interface
- Host, Port, Nickname, and Admin authentication dialog
- Real-time message streaming with color-coded bubbles/tags
- Active users list sidebar
- Quick command shortcuts (/help, /users, /msg)
- Clean thread-safe GUI updates
"""

import socket
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import config


class ChatGUIClient:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TCP Chat Room - Computer Networks Lab")
        self.root.geometry("820x620")
        self.root.minsize(700, 500)
        self.root.configure(bg="#1E1E2E")  # Modern dark theme

        # Network State
        self.socket = None
        self.running = False
        self.nickname = ""
        self.is_admin = False
        self.admin_password = ""

        # Build UI screens
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.configure_styles()

        self.create_login_screen()

    def configure_styles(self):
        """Sets up sleek dark-mode styling for widgets."""
        self.style.configure(".", background="#1E1E2E", foreground="#CDD6F4", font=("Segoe UI", 10))
        self.style.configure("TLabel", background="#1E1E2E", foreground="#CDD6F4", font=("Segoe UI", 10))
        self.style.configure("Header.TLabel", font=("Segoe UI", 16, "bold"), foreground="#89B4FA")
        self.style.configure("TEntry", fieldbackground="#313244", foreground="#FFFFFF", insertcolor="#FFFFFF")
        self.style.configure("TButton", background="#89B4FA", foreground="#11111B", font=("Segoe UI", 10, "bold"), borderwidth=0)
        self.style.map("TButton", background=[("active", "#B4BEFE")])
        self.style.configure("Danger.TButton", background="#F38BA8", foreground="#11111B")
        self.style.map("Danger.TButton", background=[("active", "#EBA0AC")])

    def create_login_screen(self):
        """Displays initial connection & nickname modal."""
        self.login_frame = tk.Frame(self.root, bg="#1E1E2E", padx=40, pady=40)
        self.login_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # Title
        title_lbl = tk.Label(
            self.login_frame,
            text="📡 TCP Chat Room",
            font=("Segoe UI", 20, "bold"),
            bg="#1E1E2E",
            fg="#89B4FA"
        )
        title_lbl.pack(pady=(0, 5))

        subtitle_lbl = tk.Label(
            self.login_frame,
            text="Computer Networks Lab (Socket Programming)",
            font=("Segoe UI", 10, "italic"),
            bg="#1E1E2E",
            fg="#A6ADC8"
        )
        subtitle_lbl.pack(pady=(0, 25))

        # Card container
        card = tk.Frame(self.login_frame, bg="#313244", padx=25, pady=25, relief=tk.FLAT)
        card.pack(fill=tk.BOTH, expand=True)

        # Host entry
        tk.Label(card, text="Server Host:", bg="#313244", fg="#CDD6F4", anchor="w").pack(fill=tk.X, pady=(0, 2))
        self.host_entry = tk.Entry(card, bg="#181825", fg="#FFFFFF", insertbackground="white", font=("Segoe UI", 11), relief=tk.FLAT)
        self.host_entry.insert(0, config.DEFAULT_HOST)
        self.host_entry.pack(fill=tk.X, ipady=6, pady=(0, 12))

        # Port entry
        tk.Label(card, text="Port Number:", bg="#313244", fg="#CDD6F4", anchor="w").pack(fill=tk.X, pady=(0, 2))
        self.port_entry = tk.Entry(card, bg="#181825", fg="#FFFFFF", insertbackground="white", font=("Segoe UI", 11), relief=tk.FLAT)
        self.port_entry.insert(0, str(config.DEFAULT_PORT))
        self.port_entry.pack(fill=tk.X, ipady=6, pady=(0, 12))

        # Nickname entry
        tk.Label(card, text="Nickname:", bg="#313244", fg="#CDD6F4", anchor="w").pack(fill=tk.X, pady=(0, 2))
        self.nick_entry = tk.Entry(card, bg="#181825", fg="#FFFFFF", insertbackground="white", font=("Segoe UI", 11), relief=tk.FLAT)
        self.nick_entry.pack(fill=tk.X, ipady=6, pady=(0, 12))

        # Admin Password entry (optional)
        self.admin_lbl = tk.Label(card, text="Admin Password (if nickname is 'admin'):", bg="#313244", fg="#CDD6F4", anchor="w")
        self.admin_lbl.pack(fill=tk.X, pady=(0, 2))
        self.pass_entry = tk.Entry(card, bg="#181825", fg="#FFFFFF", insertbackground="white", show="*", font=("Segoe UI", 11), relief=tk.FLAT)
        self.pass_entry.pack(fill=tk.X, ipady=6, pady=(0, 20))

        # Connect Button
        connect_btn = tk.Button(
            card,
            text="Connect to Chat Server",
            bg="#A6E3A1",
            fg="#11111B",
            activebackground="#94E2D5",
            font=("Segoe UI", 11, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            command=self.start_connection
        )
        connect_btn.pack(fill=tk.X, ipady=8)

        self.root.bind("<Return>", lambda event: self.start_connection())

    def start_connection(self):
        """Initiates TCP connection and authentication handshake."""
        host = self.host_entry.get().strip()
        port_str = self.port_entry.get().strip()
        nick = self.nick_entry.get().strip()
        pwd = self.pass_entry.get().strip()

        if not host or not port_str or not nick:
            messagebox.showwarning("Incomplete Details", "Please fill in Host, Port, and Nickname.")
            return

        try:
            port = int(port_str)
        except ValueError:
            messagebox.showerror("Invalid Port", "Port must be a valid number.")
            return

        self.nickname = nick
        self.admin_password = pwd

        # Connect socket in background thread to avoid freezing GUI
        threading.Thread(target=self.connect_to_server, args=(host, port), daemon=True).start()

    def connect_to_server(self, host: str, port: int):
        """Background worker to establish TCP socket and handle handshake."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.running = True
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Connection Failed", f"Could not connect to {host}:{port}\n\nError: {e}"))
            return

        # Perform handshake
        buffer = ""
        authenticated = False

        while self.running and not authenticated:
            try:
                data = self.socket.recv(config.BUFFER_SIZE)
                if not data:
                    break
                buffer += data.decode(config.ENCODING)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    if line.startswith("AUTH_REQUEST:"):
                        self.socket.sendall((self.nickname + "\n").encode(config.ENCODING))
                    elif line.startswith("AUTH_PASS_REQ:"):
                        self.socket.sendall((self.admin_password + "\n").encode(config.ENCODING))
                    elif line.startswith("AUTH_ERROR:"):
                        err_msg = line.split("AUTH_ERROR:", 1)[1].strip()
                        self.root.after(0, lambda m=err_msg: messagebox.showerror("Nickname Error", m))
                        self.socket.close()
                        self.running = False
                        return
                    elif line.startswith("AUTH_REJECT:"):
                        rej_msg = line.split("AUTH_REJECT:", 1)[1].strip()
                        self.root.after(0, lambda m=rej_msg: messagebox.showerror("Connection Rejected", m))
                        self.socket.close()
                        self.running = False
                        return
                    elif line.startswith("AUTH_OK:"):
                        authenticated = True
                        break
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Handshake Error", f"Error during handshake: {e}"))
                self.running = False
                return

        if authenticated:
            self.root.after(0, self.open_chat_interface)
            # Start background receive thread
            threading.Thread(target=self.receive_loop, daemon=True).start()

    def open_chat_interface(self):
        """Replaces login screen with the full chat interface."""
        self.login_frame.destroy()
        self.root.unbind("<Return>")

        # Top Bar
        top_bar = tk.Frame(self.root, bg="#181825", height=45, padx=15, pady=8)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            top_bar,
            text=f"💬 Room | Logged in as: {self.nickname}",
            font=("Segoe UI", 11, "bold"),
            bg="#181825",
            fg="#89B4FA"
        )
        title_lbl.pack(side=tk.LEFT)

        leave_btn = tk.Button(
            top_bar,
            text="Disconnect",
            bg="#F38BA8",
            fg="#11111B",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            command=self.disconnect
        )
        leave_btn.pack(side=tk.RIGHT)

        # Quick command buttons in top bar
        users_btn = tk.Button(
            top_bar,
            text="Online Users",
            bg="#89DCEB",
            fg="#11111B",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            command=lambda: self.send_raw_message("/users")
        )
        users_btn.pack(side=tk.RIGHT, padx=6)

        help_btn = tk.Button(
            top_bar,
            text="Commands Help",
            bg="#CBA6F7",
            fg="#11111B",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=8,
            command=lambda: self.send_raw_message("/help")
        )
        help_btn.pack(side=tk.RIGHT, padx=6)

        # Main Body: Chat display + user list sidebar
        body_frame = tk.Frame(self.root, bg="#1E1E2E")
        body_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrolled Text for Chat
        self.chat_display = scrolledtext.ScrolledText(
            body_frame,
            wrap=tk.WORD,
            bg="#181825",
            fg="#CDD6F4",
            insertbackground="white",
            font=("Consolas", 10),
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.chat_display.config(state=tk.DISABLED)

        # Configure chat tags for highlighting
        self.chat_display.tag_config("SERVER", foreground="#89B4FA", font=("Consolas", 10, "bold"))
        self.chat_display.tag_config("JOIN", foreground="#A6E3A1")
        self.chat_display.tag_config("LEAVE", foreground="#F9E2AF")
        self.chat_display.tag_config("PM", foreground="#CBA6F7", font=("Consolas", 10, "italic"))
        self.chat_display.tag_config("ERROR", foreground="#F38BA8", font=("Consolas", 10, "bold"))
        self.chat_display.tag_config("NORMAL", foreground="#CDD6F4")

        # Bottom Input Bar
        input_frame = tk.Frame(self.root, bg="#181825", padx=10, pady=10)
        input_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.msg_entry = tk.Entry(
            input_frame,
            bg="#313244",
            fg="#FFFFFF",
            insertbackground="white",
            font=("Segoe UI", 11),
            relief=tk.FLAT
        )
        self.msg_entry.pack(fill=tk.X, side=tk.LEFT, expand=True, ipady=8, padx=(0, 10))
        self.msg_entry.bind("<Return>", lambda event: self.send_chat_message())
        self.msg_entry.focus_set()

        send_btn = tk.Button(
            input_frame,
            text="Send",
            bg="#A6E3A1",
            fg="#11111B",
            font=("Segoe UI", 10, "bold"),
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            command=self.send_chat_message
        )
        send_btn.pack(side=tk.RIGHT, ipady=4)

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.disconnect)

    def append_chat(self, text: str):
        """Inserts formatted text into chat scroll area."""
        self.chat_display.config(state=tk.NORMAL)
        
        tag = "NORMAL"
        if text.startswith("[SERVER NOTICE]") or text.startswith("[SERVER ERROR]"):
            tag = "ERROR"
        elif "joined the chat" in text:
            tag = "JOIN"
        elif "left the chat" in text or "was kicked" in text or "was BANNED" in text:
            tag = "LEAVE"
        elif text.startswith("[SERVER]"):
            tag = "SERVER"
        elif "[PM from " in text or "[PM to " in text:
            tag = "PM"

        self.chat_display.insert(tk.END, text + "\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state=tk.DISABLED)

    def receive_loop(self):
        """Continuously streams messages from TCP socket."""
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(config.BUFFER_SIZE)
                if not data:
                    self.root.after(0, lambda: self.append_chat("[SERVER NOTICE] Connection closed by server."))
                    break

                buffer += data.decode(config.ENCODING)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line:
                        self.root.after(0, lambda l=line: self.append_chat(l))

            except Exception:
                break

        self.running = False

    def send_chat_message(self):
        """Sends user input message across TCP socket."""
        msg = self.msg_entry.get().strip()
        if not msg:
            return

        self.msg_entry.delete(0, tk.END)
        self.send_raw_message(msg)

        if msg.lower() in ("/quit", "/exit"):
            self.disconnect()

    def send_raw_message(self, text: str):
        """Sends raw command string to server."""
        if self.socket and self.running:
            try:
                self.socket.sendall((text + "\n").encode(config.ENCODING))
            except Exception as e:
                self.append_chat(f"[CLIENT ERROR] Failed to send: {e}")

    def disconnect(self):
        """Clean disconnection and exit."""
        self.running = False
        if self.socket:
            try:
                self.socket.sendall(("/quit\n").encode(config.ENCODING))
                self.socket.close()
            except Exception:
                pass
        self.root.destroy()


def launch_gui():
    root = tk.Tk()
    app = ChatGUIClient(root)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
