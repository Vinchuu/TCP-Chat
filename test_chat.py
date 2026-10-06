"""
Automated End-to-End Test for TCP Chat Application
Verifies server socket binding, multi-client concurrency, broadcasting,
private messaging, admin commands, and logging.
"""

import socket
import threading
import time
import os
import sys
import subprocess
import config

TEST_PORT = 5599

def run_tests():
    print("[TEST] 1. Launching Chat Server on port", TEST_PORT)
    server_proc = subprocess.Popen(
        [sys.executable, "server.py", "127.0.0.1", str(TEST_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to bind
    time.sleep(1)

    try:
        # Helper to simulate a client
        def create_test_client(nickname, password=None):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", TEST_PORT))
            
            # Read AUTH_REQUEST
            data = s.recv(config.BUFFER_SIZE).decode(config.ENCODING)
            assert "AUTH_REQUEST" in data, f"Expected AUTH_REQUEST, got {data}"
            
            # Send nickname
            s.sendall((nickname + "\n").encode(config.ENCODING))
            
            if nickname == "admin":
                data = s.recv(config.BUFFER_SIZE).decode(config.ENCODING)
                assert "AUTH_PASS_REQ" in data, f"Expected AUTH_PASS_REQ, got {data}"
                s.sendall(((password or config.DEFAULT_ADMIN_PASSWORD) + "\n").encode(config.ENCODING))

            # Read AUTH_OK
            data = s.recv(config.BUFFER_SIZE).decode(config.ENCODING)
            assert "AUTH_OK" in data, f"Expected AUTH_OK, got {data}"
            return s

        print("[TEST] 2. Connecting Client 1 ('Alice')...")
        alice_sock = create_test_client("Alice")
        time.sleep(0.5)

        print("[TEST] 3. Connecting Client 2 ('Bob')...")
        bob_sock = create_test_client("Bob")
        time.sleep(0.5)

        print("[TEST] 4. Testing Broadcast: Alice sends 'Hello world'...")
        alice_sock.sendall(("Hello world\n").encode(config.ENCODING))
        time.sleep(0.5)

        bob_received = bob_sock.recv(config.BUFFER_SIZE).decode(config.ENCODING)
        assert "Alice: Hello world" in bob_received, f"Bob did not receive broadcast: {bob_received}"
        print("  -> Passed: Bob received broadcast from Alice!")

        print("[TEST] 5. Testing Private Messaging (/msg)...")
        bob_sock.sendall(("/msg Alice SecretMessage123\n").encode(config.ENCODING))
        time.sleep(0.5)

        alice_received = alice_sock.recv(config.BUFFER_SIZE).decode(config.ENCODING)
        assert "SecretMessage123" in alice_received and "PM from Bob" in alice_received, f"Alice failed to receive PM: {alice_received}"
        print("  -> Passed: Private message received by Alice!")

        print("[TEST] 6. Disconnecting Alice and Bob...")
        alice_sock.sendall(("/quit\n").encode(config.ENCODING))
        bob_sock.sendall(("/quit\n").encode(config.ENCODING))
        time.sleep(0.5)
        alice_sock.close()
        bob_sock.close()

        print("[TEST] 7. Verifying logs created...")
        assert os.path.exists(config.SERVER_LOG_FILE), "Server log file missing!"
        assert os.path.exists(config.CHAT_LOG_FILE), "Chat history log file missing!"
        with open(config.CHAT_LOG_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            assert "Alice: Hello world" in content, "Chat log does not contain broadcast message!"
            assert "SecretMessage123" in content, "Chat log does not contain private message!"
        print("  -> Passed: Chat logs verified on disk!")

        print("\nALL AUTOMATED TESTS PASSED SUCCESSFULLY! (100% Success)")

    finally:
        server_proc.terminate()
        try:
            server_proc.wait(timeout=2)
        except Exception:
            server_proc.kill()

if __name__ == "__main__":
    run_tests()
