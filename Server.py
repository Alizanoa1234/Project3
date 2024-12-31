import socket
from api import BUFFER_SIZE, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, HEADER_SIZE

# max_msg_size = 400

def get_server_parameters():
    """
    מאפשר לשרת לבחור אם להגדיר את הפרמטרים מקובץ או באמצעות קלט מהמשתמש.
    """
    source = input("Do you want to provide max_msg_size from file or input (file/input)? Default is file: ").strip().lower()
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
        max_msg_size = int(max_msg_size) if max_msg_size.isdigit() else 400
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
                    print(f"this is max_msg_size: {int(line.split(":", 1)[1].strip())}")
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
    # קבלת פרמטרים לשרת


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server started on {host}:{port}. Waiting for connections...")

        last_acknowledged = -1
        buffer = {}

        while True:  # לולאה חיצונית להאזנה לחיבורים חדשים
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")
            server_parameters = get_server_parameters()
            max_msg_size = server_parameters["maximum_msg_size"]

            try:
                while True:  # לולאה פנימית להודעות מאותו לקוח
                    # קריאת הודעה או בקשה מהלקוח
                    message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                    if not message:
                        print("Client disconnected.")
                        break  # יציאה מהלולאה אם הלקוח סגר את החיבור

                    print(f"Received message: {message}")

                    if message == "GET_MAX_MSG_SIZE":
                        # שליחת גודל הודעה מקסימלי ללקוח
                        response = str(max_msg_size)
                        client_socket.send(response.encode('utf-8'))
                        print(f"Sent max message size: {response}")
                        continue  # המשך להאזנה להודעות נוספות

                    # טיפול בהודעות רגילות
                    header = message[:HEADER_SIZE]
                    payload = message[HEADER_SIZE:]
                    sequence_number = int(header[:4].strip())

                    print(f"Received: Sequence Number: {sequence_number}, Payload: {payload}")

                    # ניהול ACK ושמירה על הסדר
                    if sequence_number == last_acknowledged + 1:
                        print(f"Message {sequence_number} received in order.")
                        last_acknowledged = sequence_number

                        while last_acknowledged + 1 in buffer:
                            print(f"Message {last_acknowledged + 1} now in order.")
                            last_acknowledged += 1
                            del buffer[last_acknowledged]
                    else:
                        print(f"Message {sequence_number} received out of order. Storing in buffer.")
                        buffer[sequence_number] = payload

                    # שליחת ACK
                    ack = f"ACK{last_acknowledged}".ljust(HEADER_SIZE)
                    client_socket.send(ack.encode('utf-8'))
                    print(f"Sent ACK: {last_acknowledged}")

            except ConnectionResetError:
                print("Connection was reset by the client.")
            finally:
                client_socket.close()
                print(f"Connection with {client_address} closed.")


if __name__ == "__main__":
     start_server()
