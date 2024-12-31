

import socket

API_BUFFERSIZE = 1024
HEADER_SIZE = 10

def create_header(sequence_number, payload_size):

    return f"{sequence_number:04}{payload_size:04}".ljust(HEADER_SIZE)

def get_message_to_send(source="user"):
    """
    Reads the message to send.
    If source = "file", reads from client_config.txt.
    If source = "user", prompts the user for input.
    """
    if source == "file":
        try:
            with open('config.txt', 'r') as file:
                for line in file:
                    if line.startswith("message"):
                        return line.split(":")[1].strip()
        except FileNotFoundError:
            print("Configuration file not found. Falling back to user input.")
        except Exception as e:
            print(f"Error reading configuration file: {e}")
            print("Falling back to user input.")
    # User input in case of file error or if "user" is chosen
    return input("Enter the message to send: ")

def start_client():
    host = '127.0.0.1'
    port = 9999

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))
        print("Connected to server.")
        # Choose message source: file or user input
        source = input("Enter message source (file/user): ").strip().lower()
        if source not in ["file", "user"]:
            print("Invalid input. Defaulting to 'user'.")
            source = "user"

        # Send request for max message size
        request = "GET_MAX_MSG_SIZE"
        client_socket.send(request.encode('utf-8'))
        max_msg_size = int(client_socket.recv(API_BUFFERSIZE).decode('utf-8'))
        print(f"Received max message size from server: {max_msg_size}")

        # Calculate payload size
        payload_size = max_msg_size - HEADER_SIZE
        if payload_size <= 0:
            print("Error: HEADER_SIZE is larger than or equal to max_msg_size.")
            return

        # Read the message to send
        message = get_message_to_send(source)
        print(f"Message to send: {message}")

        # Send message to server (split if message size exceeds limit)
        if len(message) > payload_size:
            print("Message exceeds max payload size, splitting into parts.")
            parts = [message[i:i+payload_size] for i in range(0, len(message), payload_size)]
            for i, part in enumerate(parts):
                header = create_header(i, len(part))  # Create header for each part
                full_message = header + part  # Combine header with payload
                print(f"Sending part {i+1}/{len(parts)}: {full_message}")
                client_socket.send(full_message.encode('utf-8'))
        else:
            header = create_header(0, len(message))  # Header for a single part
            full_message = header + message
            print(f"Sending message: {full_message}")
            client_socket.send(full_message.encode('utf-8'))

        # Receive response from server
        response = client_socket.recv(API_BUFFERSIZE).decode('utf-8')
        print(f"Received response from server: {response}")

if __name__ == "__main__":
    start_client()

