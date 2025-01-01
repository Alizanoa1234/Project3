import socket
import time

from api import BUFFER_SIZE, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, HEADER_SIZE
import math
def create_header(sequence_number, payload_size, sequence_digits, payload_digits):
    sequence_number_str = f"{sequence_number:0{sequence_digits}d}"  # מספר סידורי בגודל קבוע
    payload_size_str = f"{payload_size:0{payload_digits}d}"  # גודל payload בגודל קבוע
    return sequence_number_str + payload_size_str


def calculate_header_size(num_segments, max_msg_size_from_server):
    """
    מחשב את מספר הספרות הדרושות למספר הסידורי ולגודל ה-payload.
    """
    sequence_digits = len(str(num_segments))  # ספרות למספר סידורי
    payload_digits = len(str(max_msg_size_from_server))  # ספרות ל-Payload
    return sequence_digits, payload_digits

def calculate_payload_digits(max_msg_size):
    """
    מחשב כמה ספרות נדרשות לייצוג ה-payload בגודל max_msg_size.
    """
    return len(str(max_msg_size))


def read_config_file(filename='config.txt'):
    """
    קורא את הפרמטרים מקובץ קונפיגורציה.
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


def get_all_client_parameters():
    """
    מאפשר למשתמש לבחור את מקור הפרמטרים (קובץ או קלט ידני) ומחזיר את הפרמטרים.
    """
    # קריאת הפרמטרים מהקובץ
    config = read_config_file('config.txt')

    # הודעה
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

    # גודל חלון
    source = input("Do you want to provide the window size from file or input (file/input)? ").strip().lower()
    if source == "file":
        window_size = int(config.get('window_size', '4'))
        print(f"Window size loaded from file: {window_size}")
    elif source == "input":
        window_size = input("Enter the window size: ").strip()
        try:
            window_size = int(window_size)  # ניסיון להמיר למספר שלם
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
            timeout = int(timeout)  # המרה למספר שלם
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

        # Get all parameters (message, window size, timeout)
        parameters = get_all_client_parameters()
        message = parameters["message"]
        window_size = parameters["window_size"]
        timeout = parameters["timeout"]  # Retrieve the timeout value

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

        # Calculate payload size
        payload_size = max_msg_size_from_server
        print(f"Payload size set to: {payload_size}")
        if payload_size <= 0:
            print("Error: HEADER_SIZE is larger than or equal to MAX_MSG_SIZE. Aborting.")
            return

        total_message_size = len(message)
        num_segments = math.ceil(len(message) / max_msg_size_from_server)
        sequence_digits, payload_digits = calculate_header_size(num_segments, max_msg_size_from_server)

        # Split the message into parts
        parts = [message[i:i + payload_size] for i in range(0, total_message_size, payload_size)]

        print(f"Message split into {len(parts)} parts.")
        payload_size_str = f"{payload_size:0{payload_digits}d}"  # מייצג את ה-payload בגודל המתאים
        print(f"Payload size representation: {payload_size_str}")

        window_start = 0
        unacknowledged = set(range(len(parts)))  # Track unacknowledged parts

        # Sliding window mechanism with timeout
        try:
            while unacknowledged:
                window_end = min(window_start + window_size, len(parts))
                print(f"Current window: {window_start} to {window_end - 1}")

                # Send messages in the current window
                for i in range(window_start, window_end):
                    if i in unacknowledged:
                        header = create_header(i, len(parts[i]))
                        full_message = header + parts[i]
                        print(f"[Sending] Part {i + 1}/{len(parts)}: {full_message} (Size: {len(full_message)} bytes)")
                        client_socket.send(full_message.encode('utf-8'))

                # Start timer for timeout
                timer_start = time.time()

                while time.time() - timer_start < timeout:
                    try:
                        client_socket.settimeout(timeout - (time.time() - timer_start))
                        response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                        ack_num = int(response.replace("ACK", "").strip())
                        print(f"[ACK] Received ACK for message: {ack_num}")

                        # Process cumulative ACKs
                        for seq in range(window_start, ack_num + 1):
                            if seq in unacknowledged:
                                unacknowledged.remove(seq)
                        window_start = ack_num + 1
                        break  # Exit timeout loop on successful ACK
                    except socket.timeout:
                        print(f"[Timeout] No ACK received within {timeout} seconds. Retrying...")
                        # Retry sending only unacknowledged parts
                        for i in range(window_start, window_end):
                            if i in unacknowledged:
                                header = create_header(i, len(parts[i]))
                                full_message = header + parts[i]
                                print(
                                    f"[Retrying] Part {i + 1}/{len(parts)}: {full_message} (Size: {len(full_message)} bytes)")
                                client_socket.send(full_message.encode('utf-8'))
                        break
                    except (ValueError, ConnectionResetError):
                        print("[Error] Acknowledgment processing failed. Retrying unacknowledged parts.")
                        break
        finally:
            # Final cleanup and connection closure
            print("All messages sent and acknowledged.")
            print("Closing the connection.")
            client_socket.shutdown(socket.SHUT_WR)  # Graceful shutdown
            client_socket.close()


if __name__ == "__main__":
    start_client()
        # # שליחת הודעה לשרת (עם פיצול אם צריך)
        # if len(message) > payload_size:
        #     print("Message exceeds max payload size. Splitting into parts.")
        #     parts = [message[i:i + payload_size] for i in range(0, len(message), payload_size)]
        #     print(f"Total parts to send: {len(parts)}")  # הדפסת מספר החלקים
        #     for i, part in enumerate(parts):
        #         header = create_header(i, len(part))
        #         full_message = header + part
        #         print(f"Part {i + 1}/{len(parts)}: {len(part)} bytes, Content: {part}")
        #         client_socket.send(full_message.encode('utf-8'))
        # else:
        #     header =
    #     create_header(0, len(message))
        #     full_message = header + message
        #     print(f"Sending message: {full_message}")
        #     client_socket.send(full_message.encode('utf-8'))
        #
        # # קבלת תשובה מהשרת
        # response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
        # print(f"Received response from server: {response}")