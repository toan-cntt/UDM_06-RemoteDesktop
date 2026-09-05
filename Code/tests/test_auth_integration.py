import json
import socket
import threading

from common.protocol import (
    send_message,
    receive_message,
    CMD_AUTH_REQ,
    CMD_AUTH_RES,
)

from server.auth import (
    init_credentials,
    verify_credentials,
)


def run_auth_server(server_socket):
    client_socket, client_address = server_socket.accept()

    try:
        cmd, payload = receive_message(client_socket)

        if cmd != CMD_AUTH_REQ:
            send_message(
                client_socket,
                CMD_AUTH_RES,
                bytearray([0])
            )
            return

        req = json.loads(payload.decode("utf-8"))

        ok = verify_credentials(
            req.get("id", ""),
            req.get("password", ""),
            client_ip=client_address[0],
        )

        send_message(
            client_socket,
            CMD_AUTH_RES,
            bytearray([1 if ok else 0])
        )

    finally:
        client_socket.close()


def test_authentication_success_over_tcp():
    # Credential cố định để test
    init_credentials(fixed_id="123456")

    # Password cố định cho test
    import server.auth as auth

    auth._current_password = "5678"

    server_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server_socket.bind(("127.0.0.1", 0))
    server_socket.listen(1)

    port = server_socket.getsockname()[1]

    server_thread = threading.Thread(
        target=run_auth_server,
        args=(server_socket,),
        daemon=True
    )

    server_thread.start()

    client_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    try:
        client_socket.connect(("127.0.0.1", port))

        payload = json.dumps({
            "id": "123456",
            "password": "5678"
        }).encode("utf-8")

        send_message(
            client_socket,
            CMD_AUTH_REQ,
            payload
        )

        cmd, response = receive_message(client_socket)

        assert cmd == CMD_AUTH_RES
        assert response == b"\x01"

    finally:
        client_socket.close()
        server_socket.close()

    server_thread.join(timeout=1)