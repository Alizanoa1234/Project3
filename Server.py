import socket
import time
from api import BUFFER_SIZE, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, HEADER_SIZE


# Function to request and receive header size and number of segments
def receive_header_size_and_num_segment(client_socket):
    """
    Requests the header size and number of segments from the client.
    """
    try:
        client_socket.send("GET_HEADER_SIZE_AND_NUM_SEGMENTS\n".encode('utf-8'))

        # Receive header size, number of segments, and window size
        header_and_segments_data = client_socket.recv(10).decode('utf-8').strip()
        window_size_data = client_socket.recv(10).decode('utf-8').strip()

        if "," not in header_and_segments_data:
            print("[Error] Data format is incorrect. Missing ',' between header size and number of segments.")
            client_socket.send("ERROR_INVALID_FORMAT\n".encode('utf-8'))
            return None, None

        header_size, num_segments = header_and_segments_data.split(",")

        # Convert header size and segments to integers and handle errors
        try:
            header_size = int(header_size)
            num_segments = int(num_segments)
            window_size = int(window_size_data)
        except ValueError:
            print("[Error] One of the values is not a valid integer.")
            client_socket.send("ERROR_INVALID_VALUES\n".encode('utf-8'))
            return None, None

        print(f"[Server] Received header size: {header_size} and num segments: {num_segments}")
        client_socket.send("ACK_HEADER_AND_SEGMENTS\n".encode('utf-8'))
        print("[Server] Sent acknowledgment for header size and number of segments.")
        return header_size, num_segments, window_size

    except Exception as e:
        print(f"[Error] An unexpected error occurred: {e}")
        return None


# Function to load server parameters
def get_server_parameters():
    """
    Reads the max_msg_size from a file or input.
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
            max_msg_size = int(max_msg_size)
        except ValueError:
            print("Invalid input. Using default max message size of 400.")
            max_msg_size = 400
        print(f"max_msg_size set by user input: {max_msg_size}")

    print(f"Final max_msg_size: {max_msg_size}")
    return {"maximum_msg_size": max_msg_size}


# Function to read the max_msg_size from a configuration file
def get_max_msg_size(filename='config.txt'):
    """
    Reads the max_msg_size from the configuration file.
    """
    try:
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith("max_msg_size:"):
                    return int(line.split(":", 1)[1].strip())
    except (FileNotFoundError, ValueError) as e:
        print(f"[Warning] Error reading configuration file: {e}")
    return None


# Main server loop
def start_server():
    host = DEFAULT_SERVER_HOST
    port = DEFAULT_SERVER_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server started on {host}:{port}. Waiting for connections...")

        last_acknowledged = -1  # Last in-order message acknowledged

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")
            max_msg_size = get_server_parameters()["maximum_msg_size"]

            try:
                # Handle client requests
                message = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not message:
                    print("Client disconnected.")
                    break

                if message == "GET_MAX_MSG_SIZE":
                    client_socket.send(str(max_msg_size).encode('utf-8'))
                    print(f"Sent max message size: {max_msg_size}")

                # Get header size, number of segments, and window size
                print("Requesting header size and num segments from client...")
                header_size, num_segments, window_size = receive_header_size_and_num_segment(client_socket)
                if header_size is None:
                    print("Failed to receive header size and num segments. Closing connection.")
                    client_socket.close()
                    break

                # Receive and process client messages
                unordered_buffer = {}
                while last_acknowledged < num_segments - 1:
                    part_count = 0
                    batch_buffer = ""

                    while part_count < window_size and last_acknowledged < num_segments - 1:
                        try:
                            client_socket.settimeout(20)
                            data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                            if not data:
                                print("No more data from client.")
                                break

                            batch_buffer += data
                            while "\n" in batch_buffer:
                                message, batch_buffer = batch_buffer.split("\n", 1)
                                if message:
                                    # Parse sequence number and payload
                                    header = message[:header_size]
                                    payload = message[header_size:header_size + max_msg_size]
                                    sequence_number = int(header.strip())

                                    # Handle in-order and out-of-order messages
                                    if sequence_number == last_acknowledged + 1:
                                        print(f"Message {sequence_number} received in order.")
                                        last_acknowledged = sequence_number
                                        part_count += 1

                                    elif sequence_number > last_acknowledged:
                                        unordered_buffer[sequence_number] = payload

                        except socket.timeout:
                            print("Timeout occurred.")
                            break

                    # Send cumulative ACK
                    ack = f"ACK{last_acknowledged}".ljust(header_size)
                    client_socket.send(ack.encode('utf-8'))
                    print(f"Sent ACK for message: {last_acknowledged}")

                    if last_acknowledged == num_segments - 1:
                        print("All messages received. Sending FINAL_ACK.")
                        client_socket.send("FINAL_ACK".encode('utf-8'))
                        break

            except Exception as e:
                print(f"Error during connection: {e}")
            finally:
                client_socket.close()
                print(f"Connection with {client_address} closed.")


if __name__ == "__main__":
    start_server()
