"""
Command-Line Interface (CLI) TCP Chat Client
Computer Networks Lab (CNL) Project

Features:
- Connects to TCP Chat Server via socket API
- Separate receive thread to handle incoming stream data without blocking user typing
- Interactive user authentication (standard user or admin)
- Full support for public broadcast, private messages (/msg), and commands (/help, /users, /quit)
- Graceful exit and clean error recovery
"""

import socket
import threading
import sys
import os
import getpass
import config
from utils import Colors


class ChatClient:
    def __init__(self, host: str = config.DEFAULT_HOST, port: int = config.DEFAULT_PORT):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.authenticated = False
        self.nickname = ""

    def connect(self) -> bool:
        """Establishes TCP connection to the chat server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.running = True
            return True
        except ConnectionRefusedError:
            print(f"{Colors.RED}[ERROR] Connection Refused: Ensure the chat server is running on {self.host}:{self.port}{Colors.RESET}")
            return False
        except Exception as e:
            print(f"{Colors.RED}[ERROR] Failed to connect: {e}{Colors.RESET}")
            return False

    def receive_loop(self):
        """Listens for incoming messages from the server."""
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(config.BUFFER_SIZE)
                if not data:
                    if self.running:
                        print(f"\n{Colors.YELLOW}[NOTICE] Connection closed by the server.{Colors.RESET}")
                    break

                buffer += data.decode(config.ENCODING)
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue

                    # Handle server protocol messages
                    if line.startswith("AUTH_"):
                        self.handle_auth_message(line)
                    else:
                        # Display regular or server messages with color highlights
                        self.display_message(line)

            except (ConnectionResetError, ConnectionAbortedError):
                if self.running:
                    print(f"\n{Colors.YELLOW}[NOTICE] Connection lost with the server.{Colors.RESET}")
                break
            except Exception as e:
                if self.running:
                    print(f"\n{Colors.RED}[ERROR] Error receiving data: {e}{Colors.RESET}")
                break

        self.running = False

    def handle_auth_message(self, message: str):
        """Processes authentication challenges sent by the server."""
        if message.startswith("AUTH_REQUEST:"):
            # Server asks for nickname
            while True:
                nick = input(f"{Colors.CYAN}Enter your nickname: {Colors.RESET}").strip()
                if nick:
                    self.nickname = nick
                    self.socket.sendall((nick + "\n").encode(config.ENCODING))
                    break

        elif message.startswith("AUTH_PASS_REQ:"):
            # Admin password prompt (masked input)
            pwd = getpass.getpass(f"{Colors.YELLOW}Enter Admin Password: {Colors.RESET}").strip()
            self.socket.sendall((pwd + "\n").encode(config.ENCODING))

        elif message.startswith("AUTH_ERROR:"):
            error_reason = message.split("AUTH_ERROR:", 1)[1].strip()
            print(f"{Colors.RED}[AUTH ERROR] {error_reason}{Colors.RESET}")

        elif message.startswith("AUTH_REJECT:"):
            reject_reason = message.split("AUTH_REJECT:", 1)[1].strip()
            print(f"{Colors.RED}[AUTH REJECTED] {reject_reason}{Colors.RESET}")
            self.running = False
            self.socket.close()

        elif message.startswith("AUTH_OK:"):
            welcome_msg = message.split("AUTH_OK:", 1)[1].strip()
            self.authenticated = True
            print(f"{Colors.GREEN}[SUCCESS] {welcome_msg}{Colors.RESET}\n")

    def display_message(self, message: str):
        """Prints incoming messages with appropriate styling."""
        if message.startswith("[SERVER NOTICE]") or message.startswith("[SERVER ERROR]"):
            print(f"{Colors.RED}{message}{Colors.RESET}")
        elif message.startswith("[SERVER]"):
            print(f"{Colors.CYAN}{message}{Colors.RESET}")
        elif "[PM from " in message or "[PM to " in message:
            print(f"{Colors.MAGENTA}{message}{Colors.RESET}")
        else:
            print(f"{Colors.WHITE}{message}{Colors.RESET}")

    def run(self):
        """Starts client execution loop."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.GREEN}   TCP Client-Server Chat Application{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.RESET}")
        print(f"Connecting to {self.host}:{self.port} ...\n")

        if not self.connect():
            return

        # Start receive thread
        recv_thread = threading.Thread(target=self.receive_loop, daemon=True)
        recv_thread.start()

        # Wait until authenticated or disconnected
        while self.running and not self.authenticated:
            pass

        if not self.running:
            return

        print(f"{Colors.GRAY}Type your message and press Enter. Type /help for command list.{Colors.RESET}\n")

        # Main input loop
        try:
            while self.running:
                msg = input()
                if not self.running:
                    break

                stripped = msg.strip()
                if not stripped:
                    continue

                # Send to server
                try:
                    self.socket.sendall((stripped + "\n").encode(config.ENCODING))
                except Exception as e:
                    print(f"{Colors.RED}[ERROR] Failed to send message: {e}{Colors.RESET}")
                    break

                if stripped.lower() in ("/quit", "/exit"):
                    print(f"{Colors.YELLOW}Leaving chat room...{Colors.RESET}")
                    self.running = False
                    break

        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.YELLOW}Exiting chat...{Colors.RESET}")
        finally:
            self.running = False
            if self.socket:
                try:
                    self.socket.close()
                except Exception:
                    pass
            print(f"{Colors.GREEN}Disconnected.{Colors.RESET}")


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else config.DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else config.DEFAULT_PORT
    client = ChatClient(host=host, port=port)
    client.run()
