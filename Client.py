import socket
import time
import math
from api import BUFFER_SIZE, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, HEADER_SIZE

# Function to create a sequence number header for each message part
def create_header(sequence_number, header_size):
    """
    Creates a header containing the sequence number.
    """
    sequence_number_str = f"{sequence_number:0{header_size}d}"  # Fixed-size sequence number
    return sequence_number_str

# Reads parameters from a configuration file
def read_config_file(filename='config.txt'):
    """
    Reads configuration parameters from a file.
    """
    config = {}
    try:
        with open(filename, 'r') as file:
            for line in file:
                if ':' in line:
                    key, value = line.split(":", 1)
                    config[key.strip()] = value.strip()
        return config
    except FileNotFoundError:
        print(f"Configuration file '{filename}' not found. Using defaults.")
    except Exception as e:
        print(f"Error reading configuration file: {e}")
    return {}

# Retrieves user-defined or default client parameters
def get_all_client_parameters():
    """
    Allows the user to choose whether to provide input or load parameters from a file.
    """
    config = read_config_file('config.txt')  # Load from configuration file

    # Message
    source = input("Do you want to provide the message from file or input (file/input)? ").strip().lower()
    if source == "file":
        message = config.get('message', 'This is a test message')
        print(f"Message loaded from file: {message}")
    elif source == "input":
        message = input("Enter the message: ").strip()
        while not message:
            print("Message cannot be empty. Please enter a valid message.")
            message = input("Enter the message: ")
    else:
        print("Invalid choice. Defaulting to file.")
        message = config.get('message', 'This is a test message')
        print(f"Message loaded from file: {message}")

    # Window size
    source = input("Do you want to provide the window size from file or input (file/input)? ").strip().lower()
    if source == "file":
        window_size = int(config.get('window_size', '4'))
        print(f"Window size loaded from file: {window_size}")
    elif source == "input":
        window_size = input("Enter the window size: ").strip()
        try:
            window_size = int(window_size)
        except ValueError:
            print("Invalid input. Using default window size of 4.")
            window_size = 4
    else:
        print("Invalid choice. Defaulting to file.")
        window_size = int(config.get('window_size', '4'))
        print(f"Window size loaded from file: {window_size}")

    # Timeout
    source = input("Do you want to provide the timeout from file/input? ").strip().lower()
    if source == "file":
        timeout = int(config.get('timeout', '5'))
        print(f"Timeout loaded from file: {timeout}")
    elif source == "input":
        timeout = input("Enter the timeout (in seconds): ").strip()
        try:
            timeout = int(timeout)
        except ValueError:
            print("Invalid input. Using default timeout of 5 seconds.")
            timeout = 5
    else:
        print("Invalid choice. Defaulting to file.")
        timeout = int(config.get('timeout', '5'))
        print(f"Timeout loaded from file: {timeout}")

    return {
        "message": message,
        "window_size": window_size,
        "timeout": timeout,
    }

# Main client function to establish connection and send data
def start_client():
    host = DEFAULT_SERVER_HOST
    port = DEFAULT_SERVER_PORT

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        try:
            client_socket.connect((host, port))
            print("Connected to server.")
        except ConnectionRefusedError:
            print("Failed to connect to the server. Ensure the server is running.")
            return

        # Request maximum message size from the server
        request = "GET_MAX_MSG_SIZE"
        client_socket.send(request.encode('utf-8'))
        print("Requesting max message size from server...")

        try:
            # Receive the maximum message size from the server
            response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            max_msg_size_from_server = int(response)
            print(f"Received max message size from server: {max_msg_size_from_server}")
        except (ValueError, ConnectionResetError, TimeoutError) as e:
            print(f"Failed to get max message size from server: {e}")
            return

        # Get client parameters (message, window size, timeout)
        parameters = get_all_client_parameters()
        message = parameters["message"]
        window_size = parameters["window_size"]
        timeout = parameters["timeout"]

        # Calculate payload size and other message details
        payload_size = max_msg_size_from_server
        print(f"Payload size set to: {payload_size}")
        if payload_size <= 0:
            print("Error: HEADER_SIZE is larger than or equal to MAX_MSG_SIZE. Aborting.")
            return

        total_message_size = len(message)
        num_segments = math.ceil(total_message_size / max_msg_size_from_server)
        header_size = len(str(num_segments))

        try:
            response_data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            print(f"The server's message: {response_data}")
            responses = response_data.split("\n")

            ack_received = False
            for response in responses:
                response = response.strip()
                if response == "GET_HEADER_SIZE_AND_NUM_SEGMENTS":
                    print("[Client] Server requested header size and number of segments.")
                    print(f"Calculated : header size: {header_size} + num segments: {num_segments}")

                    try:
                        data_to_send = f"{header_size},{num_segments}\n"
                        client_socket.send(data_to_send.encode('utf-8'))
                        print(f"[Client] Sent header size: {header_size} and num segments: {num_segments}")

                        # Send window size separately
                        client_socket.send(f"{window_size}\n".encode('utf-8'))
                        print(f"[Client] Sent window size: {window_size}")

                    except Exception as e:
                        print(f"[Error] Failed to send header size and window size: {e}")
                        return

                    try:
                        ack_response = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
                        if ack_response == "ACK_HEADER_AND_SEGMENTS":
                            print("[Client] Server acknowledged header size and num of segment.")
                            ack_received = True
                        else:
                            print(f"[Error] Unexpected response from server: {ack_response}")
                            return
                    except Exception as e:
                        print(f"[Error] Failed to receive ACK: {e}")
                        return

            if not ack_received:
                print("[Error] ACK_HEADER_AND_SEGMENTS not received.")
                return

        except Exception as e:
            print(f"Failed to send header size and num of segment. Error: {e}")
            return

        # Split the message into segments
        parts = [message[i:i + payload_size] for i in range(0, total_message_size, payload_size)]
        print(f"Total message size: {total_message_size}")
        print(f"Message split into {len(parts)} parts.")

        window_start = 0
        unacknowledged = set(range(len(parts)))
        last_acknowledged = -1

        headers = {i: create_header(i, header_size) for i in range(len(parts))}

        # Sliding window mechanism for sending data
        try:
            while unacknowledged:
                window_end = min(window_start + window_size, len(parts))
                print(f"Current window: {window_start} to {window_end - 1}")

                # Prepare and send messages in the current window
                batch_messages = []
                for i in range(window_start, window_end):
                    if i in unacknowledged:
                        header = headers[i]
                        full_message = header + parts[i] + "\n"
                        batch_messages.append(full_message)
                        print(f" Prepared message Part {i}: {full_message}")

                if batch_messages:
                    batch_data = "".join(batch_messages)
                    client_socket.send(batch_data.encode('utf-8'))
                    print(f"[Client] Sent batch: {batch_data}")

                # Wait for ACK from the server
                timer_start = time.time()
                ack_received = False

                while time.time() - timer_start < timeout:
                    try:
                        response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                        print(f"Server response: {response}")

                        if response.startswith("ACK"):
                            ack_num = int(response.replace("ACK", "").strip())
                            print(f"[ACK] Received ACK for message: {ack_num}\n")
                            for seq in range(window_start, ack_num + 1):
                                unacknowledged.discard(seq)
                            window_start = ack_num + 1
                            ack_received = True
                            break

                    except socket.timeout:
                        print(f"[Timeout] No ACK received.")
                        break

        finally:
            if not unacknowledged:
                print("All messages sent and acknowledged.")
            else:
                print("Not all messages were acknowledged.")
            client_socket.shutdown(socket.SHUT_WR)
            client_socket.close()
            print("Connection closed.")

if __name__ == "__main__":
    start_client()
