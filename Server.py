import socket

from api import BUFFER_SIZE, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, HEADER_SIZE

# max_msg_size = 400
def receive_header_size(client_socket):
    """
    מבקש את גודל ההדר מהלקוח ומאשר את קבלתו.
    """
    try:
        # שליחת בקשה לגודל ההדר
        client_socket.send("GET_HEADER_SIZE\n".encode('utf-8'))
        print("[Server] Sent GET_HEADER_SIZE request.")

        # קבלת גודל ההדר מהלקוח
        header_size_data = client_socket.recv(10).decode('utf-8').strip()
        if not header_size_data.isdigit():
            raise ValueError(f"Invalid header size received: {header_size_data}")

        header_size = int(header_size_data)
        print(f"[Server] Received header size: {header_size}")

        # שליחת ACK על קבלת ההדר
        client_socket.send("ACK_HEADER\n".encode('utf-8'))
        print("[Server] Sent acknowledgment for header size.")

        return header_size
    except ValueError as e:
        print(f"[Error] {e}")
    except Exception as e:
        print(f"[Error] An unexpected error occurred: {e}")
        return None



def get_server_parameters():
    """
    מאפשר לשרת לבחור אם להגדיר את הפרמטרים מקובץ או באמצעות קלט מהמשתמש.
    """
    source = input(
        "Do you want to provide max_msg_size from file or input (file/input)? Default is file: ").strip().lower()
    if source not in ["file", "input"]:
        print("Invalid choice. Defaulting to file.")
        source = "file"

    if source == "file":
        max_msg_size = get_max_msg_size()
        if max_msg_size is None:
            print("max_msg_size not found in configuration file. Using default value: 400.")
            max_msg_size = 400
        else:
            print(f"max_msg_size successfully read from file: {max_msg_size}")
    else:
        max_msg_size = input("Enter the maximum message size (default: 400): ").strip()
        try:
            max_msg_size = int(max_msg_size)  # ניסיון להמיר למספר שלם
        except ValueError:
            print("Invalid input. Using default max message size of 400.")
            max_msg_size = 400
        print(f"max_msg_size set by user input: {max_msg_size}")

    print(f"Final max_msg_size: {max_msg_size}")
    return {"maximum_msg_size": max_msg_size}


def get_max_msg_size(filename='config.txt'):
    """
    קורא את הפרמטרים מקובץ קונפיגורציה.
    """
    try:
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith("max_msg_size:"):
                    # print(f"this is max_msg_size: {int(line.split(":", 1)[1].strip())}")
                    return int(line.split(":", 1)[1].strip())
        print("max_msg_size not found in configuration file.")
    except FileNotFoundError:
        print("Configuration file not found.")
    except Exception as e:
        print(f"Error reading configuration file: {e}")
    return None


def start_server():
    host = DEFAULT_SERVER_HOST
    port = DEFAULT_SERVER_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server started on {host}:{port}. Waiting for connections...")

        last_acknowledged = -1
        buffer = {}

        while True:  # External loop to handle new connections

            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")
            # todo צריך לשים טטים אאוט לכל קריאה מהלקוח?
           # client_socket.settimeout(15)
            server_parameters = get_server_parameters()
            max_msg_size = server_parameters["maximum_msg_size"]

            try:
                # Read message or request from the client
                message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not message:
                    print("Client disconnected.")
                    break  # Exit loop if client closes the connection

                if message == "GET_MAX_MSG_SIZE":
                    # Send the maximum message size to the client
                    response = str(max_msg_size)
                    client_socket.send(response.encode('utf-8'))
                    print(f"Sent max message size: {response}")


                print("Requesting header size from client...")
                header_size = receive_header_size(client_socket)
                if header_size is None:
                    print("Failed to receive header size. Closing connection.")
                    client_socket.close()
                    # אפשר לנסות להתחבר מחדש או לסיים את התהליך
                else:
                    print(f"Header size received successfully: {header_size}")
                    # המשך התהליך

                # קריאת הודעה מהלקוח
                while True:  # Internal loop for handling messages from the same client
                    try:
                        # Read message or request from the client
                        message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                        if not message:
                            print("Client disconnected.")
                            break  # Exit loop if client closes the connection

                        print(f"Received message: {message}")

                        # Handle regular messages
                        header = message[:header_size]
                        payload = message[header_size:header_size + max_msg_size]
                        print(f"Parsed message -> Header: {header}, Payload: {payload}")

                        # קריאה של מספר סידורי מתוך ה-Header
                        try:
                            sequence_number = int(header.strip())
                            print(f"Sequence number extracted: {sequence_number}")
                        except ValueError:
                            print("Error: Invalid header received. Skipping this message.")
                            continue  # Skip invalid messages

                        # עיבוד הודעה
                        print(f"Received: Sequence Number: {sequence_number}, Payload: {payload}")

                        # ניהול הודעות מאוחרות ואישורי ACK
                        if sequence_number == last_acknowledged + 1:
                            print(f"Message {sequence_number} received in order.")
                            last_acknowledged = sequence_number

                            # עיבוד הודעות מה-buffer
                            while last_acknowledged + 1 in buffer:
                                print(f"Message {last_acknowledged + 1} now in order.")
                                last_acknowledged += 1
                                del buffer[last_acknowledged]

                            # שליחת ACK
                            ack = f"ACK{last_acknowledged}".ljust(header_size)
                            client_socket.send(ack.encode('utf-8'))
                            print(f"Sent ACK: {last_acknowledged}")
                        else:
                            if sequence_number not in buffer:
                                print(f"Message {sequence_number} received out of order. Storing in buffer.")
                                buffer[sequence_number] = payload
                            else:
                                print(f"Duplicate message {sequence_number} received. Ignoring.")

                            # שליחת ACK עבור ההודעה האחרונה שנקלטה בסדר הנכון
                            ack = f"ACK{last_acknowledged}".ljust(header_size)
                            client_socket.send(ack.encode('utf-8'))
                            print(f"Sent ACK: {last_acknowledged}")

                    except socket.timeout:
                        print("Timeout occurred while waiting for client data.")
                    except ConnectionResetError:
                        print("Connection was reset by the client.")
                        break
                    except Exception as e:
                        print(f"Unexpected error while processing client message: {e}")

            except ConnectionResetError:
                print("Connection was reset by the client.")
            finally:
                client_socket.close()
                print(f"Connection with {client_address} closed.")


if __name__ == "__main__":
    start_server()
