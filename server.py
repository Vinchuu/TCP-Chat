"""
Multi-Threaded TCP Chat Server
Computer Networks Lab (CNL) Project

Features:
- Socket Programming using TCP (AF_INET, SOCK_STREAM)
- Multithreaded concurrency (handles multiple simultaneous client connections)
- Broadcasting and Unicast (Private Messaging)
- Administrative controls (Kick, Ban, Unban, User List)
- Persistent Chat & Server Event Logging
- Robust Exception Handling & Graceful Shutdown
"""

import socket
import threading
import json
import os
import sys
from datetime import datetime
import config
from utils import Colors, get_timestamp, setup_logger, format_chat_message


class ChatServer:
    def __init__(self, host: str = config.DEFAULT_HOST, port: int = config.DEFAULT_PORT):
        self.host = host
        self.port = port
        
        # State management
        self.clients = {}  # socket -> {"nickname": str, "address": tuple, "is_admin": bool}
        self.nicknames = {}  # nickname (lowercase) -> socket
        self.lock = threading.Lock()
        self.running = False
        
        # Setup directories and loggers
        os.makedirs(config.LOG_DIR, exist_ok=True)
        self.server_logger = setup_logger("server_log", config.SERVER_LOG_FILE)
        self.chat_logger = setup_logger("chat_log", config.CHAT_LOG_FILE)
        
        # Banned list storage
        self.banned_users = self.load_banned_users()
        
        # Server Socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Enable SO_REUSEADDR so port is reusable immediately after restart
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def load_banned_users(self) -> dict:
        """Loads banned nicknames and IP addresses from JSON file."""
        if os.path.exists(config.BAN_LIST_FILE):
            try:
                with open(config.BAN_LIST_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.server_logger.error(f"Error loading {config.BAN_LIST_FILE}: {e}")
        return {"nicknames": [], "ips": []}

    def save_banned_users(self):
        """Persists banned list to JSON file."""
        try:
            with open(config.BAN_LIST_FILE, "w", encoding="utf-8") as f:
                json.dump(self.banned_users, f, indent=4)
        except Exception as e:
            self.server_logger.error(f"Error saving {config.BAN_LIST_FILE}: {e}")

    def log_and_print(self, level: str, message: str, color: str = Colors.WHITE):
        """Prints formatted message to server console and logs to server.log."""
        timestamp = get_timestamp()
        console_msg = f"{Colors.GRAY}[{timestamp}]{Colors.RESET} {color}[{level}]{Colors.RESET} {message}"
        print(console_msg)
        
        log_entry = f"[{level}] {message}"
        if level == "ERROR":
            self.server_logger.error(log_entry)
        elif level == "WARN":
            self.server_logger.warning(log_entry)
        else:
            self.server_logger.info(log_entry)

    def log_chat(self, entry: str):
        """Appends a message entry to chat history log."""
        self.chat_logger.info(entry)

    def broadcast(self, message: str, exclude_socket=None):
        """
        Sends a message to all connected clients except optionally the sender.
        Thread-safe iteration.
        """
        with self.lock:
            for client_sock in list(self.clients.keys()):
                if client_sock != exclude_socket:
                    try:
                        client_sock.sendall((message + "\n").encode(config.ENCODING))
                    except Exception as e:
                        # Client disconnected unexpectedly
                        self.log_and_print("WARN", f"Failed to send to client: {e}", Colors.YELLOW)

    def send_to(self, target_socket, message: str):
        """Sends a private message or direct server response to a single socket."""
        try:
            target_socket.sendall((message + "\n").encode(config.ENCODING))
        except Exception as e:
            self.log_and_print("WARN", f"Failed to send direct message: {e}", Colors.YELLOW)

    def handle_client(self, client_socket: socket.socket, client_address: tuple):
        """
        Handles bidirectional communication with a single client in its own thread.
        """
        ip, port = client_address
        nickname = None

        try:
            # 1. IP Ban Verification
            if ip in self.banned_users.get("ips", []):
                self.send_to(client_socket, "AUTH_REJECT: Your IP address is banned from this server.")
                client_socket.close()
                self.log_and_print("WARN", f"Rejected connection from banned IP: {ip}:{port}", Colors.RED)
                return

            # 2. Handshake & Nickname Registration
            while True:
                self.send_to(client_socket, "AUTH_REQUEST: Enter your nickname")
                raw_nick = client_socket.recv(config.BUFFER_SIZE).decode(config.ENCODING).strip()
                if not raw_nick:
                    client_socket.close()
                    return

                # Nickname validation
                if len(raw_nick) > config.MAX_NICKNAME_LENGTH or len(raw_nick) < 2:
                    self.send_to(client_socket, "AUTH_ERROR: Nickname must be between 2 and 20 characters.")
                    continue

                if " " in raw_nick:
                    self.send_to(client_socket, "AUTH_ERROR: Nickname cannot contain spaces.")
                    continue

                lower_nick = raw_nick.lower()

                # Check if banned
                if lower_nick in [b.lower() for b in self.banned_users.get("nicknames", [])]:
                    self.send_to(client_socket, "AUTH_REJECT: This nickname is banned from the server.")
                    client_socket.close()
                    return

                # Check if taken
                with self.lock:
                    if lower_nick in self.nicknames:
                        self.send_to(client_socket, "AUTH_ERROR: Nickname already in use. Please choose another.")
                        continue

                # Admin authentication
                is_admin = False
                if lower_nick == config.ADMIN_NICKNAME.lower():
                    self.send_to(client_socket, "AUTH_PASS_REQ: Enter Admin Password")
                    pwd = client_socket.recv(config.BUFFER_SIZE).decode(config.ENCODING).strip()
                    if pwd != config.DEFAULT_ADMIN_PASSWORD:
                        self.send_to(client_socket, "AUTH_REJECT: Invalid admin password.")
                        client_socket.close()
                        self.log_and_print("WARN", f"Failed admin login attempt from {ip}:{port}", Colors.YELLOW)
                        return
                    is_admin = True

                # Registration Successful
                nickname = raw_nick
                with self.lock:
                    self.clients[client_socket] = {
                        "nickname": nickname,
                        "address": client_address,
                        "is_admin": is_admin
                    }
                    self.nicknames[lower_nick] = client_socket

                self.send_to(client_socket, f"AUTH_OK: Welcome {nickname} to the TCP Chat Server!")
                break

            # Announce user joined
            self.log_and_print("JOIN", f"'{nickname}' connected from {ip}:{port} (Admin={is_admin})", Colors.GREEN)
            join_msg = f"[SERVER] >>> '{nickname}' joined the chat room."
            self.broadcast(join_msg, exclude_socket=client_socket)
            self.log_chat(join_msg)

            # Send MOTD & commands hint to new client
            self.send_to(client_socket, f"[SERVER] Welcome {nickname}! Type /help for available commands.")
            self.send_to(client_socket, f"[SERVER] Active users: {len(self.clients)}. Type /users to view them.")

            # 3. Message Processing Loop
            buffer = ""
            while self.running:
                data = client_socket.recv(config.BUFFER_SIZE)
                if not data:
                    break  # Client closed connection

                buffer += data.decode(config.ENCODING)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    # Process client message or command
                    self.process_client_message(client_socket, nickname, is_admin, line)

        except (ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            self.log_and_print("ERROR", f"Exception with client {nickname or ip}: {e}", Colors.RED)
        finally:
            self.disconnect_client(client_socket, nickname)

    def process_client_message(self, client_socket: socket.socket, nickname: str, is_admin: bool, text: str):
        """Parses and executes user commands or broadcasts regular chat messages."""
        if text.startswith("/"):
            parts = text.split(" ", 2)
            command = parts[0].lower()

            if command in ("/help", "/?"):
                help_text = (
                    "\n--- Available Commands ---\n"
                    "  /help              - Display this help message\n"
                    "  /users or /list    - List online chat users\n"
                    "  /msg <user> <text> - Send a private direct message\n"
                    "  /quit or /exit     - Leave the chat server\n"
                )
                if is_admin:
                    help_text += (
                        "--- Admin Controls ---\n"
                        "  /kick <user>       - Disconnect a user from server\n"
                        "  /ban <user>        - Ban a user nickname and IP address\n"
                        "  /unban <user>      - Remove a user from ban list\n"
                        "  /banned            - View banned nicknames & IPs\n"
                        "  /clearlogs         - Clear chat history log\n"
                    )
                self.send_to(client_socket, help_text)

            elif command in ("/users", "/list"):
                with self.lock:
                    user_list = [info["nickname"] + (" (admin)" if info["is_admin"] else "") 
                                 for info in self.clients.values()]
                self.send_to(client_socket, f"[SERVER] Online Users ({len(user_list)}): " + ", ".join(user_list))

            elif command == "/msg":
                if len(parts) < 3:
                    self.send_to(client_socket, "[SERVER ERROR] Usage: /msg <username> <message>")
                    return

                target_name = parts[1].strip()
                pm_content = parts[2].strip()
                target_lower = target_name.lower()

                with self.lock:
                    target_socket = self.nicknames.get(target_lower)

                if not target_socket:
                    self.send_to(client_socket, f"[SERVER ERROR] User '{target_name}' is not online.")
                elif target_socket == client_socket:
                    self.send_to(client_socket, "[SERVER ERROR] You cannot send a private message to yourself.")
                else:
                    time_str = datetime.now().strftime("%H:%M:%S")
                    # Send to recipient
                    self.send_to(target_socket, f"[{time_str}] [PM from {nickname}]: {pm_content}")
                    # Confirmation to sender
                    self.send_to(client_socket, f"[{time_str}] [PM to {target_name}]: {pm_content}")
                    
                    # Log private communication
                    log_entry = format_chat_message(nickname, pm_content, is_private=True, recipient=target_name)
                    self.log_chat(log_entry)
                    self.log_and_print("PM", f"{nickname} -> {target_name}: {pm_content}", Colors.MAGENTA)

            elif command in ("/quit", "/exit"):
                self.send_to(client_socket, "[SERVER] Goodbye! Disconnecting...")
                client_socket.close()

            # Admin-only commands
            elif command == "/kick":
                if not is_admin:
                    self.send_to(client_socket, "[SERVER ERROR] Access Denied: Admin privileges required.")
                    return
                if len(parts) < 2:
                    self.send_to(client_socket, "[SERVER ERROR] Usage: /kick <username>")
                    return

                target_name = parts[1].strip()
                self.kick_user(target_name, reason="Kicked by administrator")

            elif command == "/ban":
                if not is_admin:
                    self.send_to(client_socket, "[SERVER ERROR] Access Denied: Admin privileges required.")
                    return
                if len(parts) < 2:
                    self.send_to(client_socket, "[SERVER ERROR] Usage: /ban <username>")
                    return

                target_name = parts[1].strip()
                self.ban_user(target_name)

            elif command == "/unban":
                if not is_admin:
                    self.send_to(client_socket, "[SERVER ERROR] Access Denied: Admin privileges required.")
                    return
                if len(parts) < 2:
                    self.send_to(client_socket, "[SERVER ERROR] Usage: /unban <username>")
                    return

                target_name = parts[1].strip()
                self.unban_user(target_name, client_socket)

            elif command == "/banned":
                if not is_admin:
                    self.send_to(client_socket, "[SERVER ERROR] Access Denied: Admin privileges required.")
                    return
                nicks = ", ".join(self.banned_users.get("nicknames", [])) or "None"
                ips = ", ".join(self.banned_users.get("ips", [])) or "None"
                self.send_to(client_socket, f"[SERVER] Banned Nicknames: {nicks}\n[SERVER] Banned IPs: {ips}")

            elif command == "/clearlogs":
                if not is_admin:
                    self.send_to(client_socket, "[SERVER ERROR] Access Denied: Admin privileges required.")
                    return
                try:
                    open(config.CHAT_LOG_FILE, "w", encoding="utf-8").close()
                    self.send_to(client_socket, "[SERVER] Chat history log has been cleared.")
                    self.log_and_print("INFO", f"Chat history cleared by admin {nickname}", Colors.CYAN)
                except Exception as e:
                    self.send_to(client_socket, f"[SERVER ERROR] Failed to clear logs: {e}")

            else:
                self.send_to(client_socket, f"[SERVER ERROR] Unknown command '{command}'. Type /help for assistance.")

        else:
            # Regular broadcast message
            time_str = datetime.now().strftime("%H:%M:%S")
            formatted_msg = f"[{time_str}] {nickname}: {text}"
            
            # Broadcast to all clients (including echo or to others)
            # Standard chat room convention: broadcast to all others and echo to sender
            self.broadcast(formatted_msg)
            
            # Save to persistent chat log & server console
            self.log_chat(formatted_msg)
            self.log_and_print("MSG", f"{nickname}: {text}", Colors.WHITE)

    def kick_user(self, target_name: str, reason: str = "Kicked by administrator"):
        """Disconnects a target user."""
        target_lower = target_name.lower()
        with self.lock:
            target_socket = self.nicknames.get(target_lower)

        if not target_socket:
            self.log_and_print("WARN", f"Kick failed: '{target_name}' is not online.", Colors.YELLOW)
            return

        self.send_to(target_socket, f"[SERVER NOTICE] You have been disconnected: {reason}")
        try:
            target_socket.close()
        except Exception:
            pass

        kick_msg = f"[SERVER] >>> '{target_name}' was kicked ({reason})."
        self.broadcast(kick_msg)
        self.log_and_print("KICK", f"'{target_name}' was kicked from the server.", Colors.RED)

    def ban_user(self, target_name: str):
        """Bans a user's nickname and IP address, saving to storage."""
        target_lower = target_name.lower()
        ip_to_ban = None

        with self.lock:
            target_socket = self.nicknames.get(target_lower)
            if target_socket and target_socket in self.clients:
                ip_to_ban = self.clients[target_socket]["address"][0]

        # Add to ban records
        if target_lower not in [b.lower() for b in self.banned_users["nicknames"]]:
            self.banned_users["nicknames"].append(target_name)
        if ip_to_ban and ip_to_ban not in self.banned_users["ips"]:
            self.banned_users["ips"].append(ip_to_ban)

        self.save_banned_users()

        # If online, disconnect immediately
        if target_socket:
            self.send_to(target_socket, "[SERVER NOTICE] You have been permanently BANNED from this server.")
            try:
                target_socket.close()
            except Exception:
                pass

        ban_msg = f"[SERVER] >>> '{target_name}' was BANNED from the server."
        self.broadcast(ban_msg)
        self.log_and_print("BAN", f"User '{target_name}' (IP: {ip_to_ban or 'N/A'}) was BANNED.", Colors.RED)

    def unban_user(self, target_name: str, admin_socket: socket.socket):
        """Removes a username from banned list."""
        matching = [b for b in self.banned_users["nicknames"] if b.lower() == target_name.lower()]
        if matching:
            for m in matching:
                self.banned_users["nicknames"].remove(m)
            self.save_banned_users()
            self.send_to(admin_socket, f"[SERVER] User '{target_name}' has been unbanned.")
            self.log_and_print("INFO", f"User '{target_name}' unbanned.", Colors.CYAN)
        else:
            self.send_to(admin_socket, f"[SERVER ERROR] User '{target_name}' not found in banned list.")

    def disconnect_client(self, client_socket: socket.socket, nickname: str):
        """Thread-safe cleanup when client disconnects."""
        was_registered = False
        with self.lock:
            if client_socket in self.clients:
                nickname = self.clients[client_socket]["nickname"]
                lower_nick = nickname.lower()
                del self.clients[client_socket]
                if lower_nick in self.nicknames:
                    del self.nicknames[lower_nick]
                was_registered = True

        try:
            client_socket.close()
        except Exception:
            pass

        if was_registered and nickname:
            leave_msg = f"[SERVER] <<< '{nickname}' has left the chat."
            self.broadcast(leave_msg)
            self.log_chat(leave_msg)
            self.log_and_print("LEAVE", f"'{nickname}' disconnected.", Colors.YELLOW)

    def start(self):
        """Starts the TCP chat server and accepts incoming connections."""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(config.MAX_QUEUED_CONNECTIONS)
            self.running = True
        except Exception as e:
            self.log_and_print("ERROR", f"Could not bind to {self.host}:{self.port} -> {e}", Colors.RED)
            sys.exit(1)

        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}   TCP Multi-Client Chat Server Running{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"  {Colors.BOLD}Host:{Colors.RESET}           {self.host}")
        print(f"  {Colors.BOLD}Port:{Colors.RESET}           {self.port}")
        print(f"  {Colors.BOLD}Protocol:{Colors.RESET}       TCP (SOCK_STREAM)")
        print(f"  {Colors.BOLD}Server Log:{Colors.RESET}     {config.SERVER_LOG_FILE}")
        print(f"  {Colors.BOLD}Chat Log:{Colors.RESET}       {config.CHAT_LOG_FILE}")
        print(f"  {Colors.BOLD}Status:{Colors.RESET}         Listening for connections... (Press Ctrl+C to stop)")
        print(f"{Colors.CYAN}{'='*60}{Colors.RESET}\n")

        self.log_and_print("SYSTEM", f"Server started listening on {self.host}:{self.port}", Colors.GREEN)

        try:
            while self.running:
                client_socket, client_address = self.server_socket.accept()
                # Spawn a new thread to handle the client
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                client_thread.start()
        except KeyboardInterrupt:
            print("\n")
            self.log_and_print("SYSTEM", "Keyboard interrupt received. Shutting down server...", Colors.YELLOW)
        finally:
            self.stop()

    def stop(self):
        """Gracefully terminates the server and closes all active sockets."""
        self.running = False
        self.broadcast("[SERVER NOTICE] Server is shutting down now. Goodbye!")

        with self.lock:
            for sock in list(self.clients.keys()):
                try:
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()
            self.nicknames.clear()

        try:
            self.server_socket.close()
        except Exception:
            pass

        self.log_and_print("SYSTEM", "Server stopped successfully.", Colors.RED)


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else config.DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else config.DEFAULT_PORT
    server = ChatServer(host=host, port=port)
    server.start()
