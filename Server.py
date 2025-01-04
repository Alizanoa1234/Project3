import socket
import time

from api import BUFFER_SIZE, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, HEADER_SIZE

# max_msg_size = 400
def receive_header_size_and_num_segment(client_socket):
    """
    מבקש את גודל ההדר מהלקוח ומאשר את קבלתו.
    """
    try:
        # שליחת בקשה לגודל ההדר
        client_socket.send("GET_HEADER_SIZE_AND_NUM_SEGMENTS\n".encode('utf-8'))
        print("[Server] Sent GET_HEADER_SIZE_AND_NUM_SEGMENTS request.")

        # קבלת גודל ההדר מהלקוח
        header_and_segments_data = client_socket.recv(10).decode('utf-8').strip()

        # if not header_and_segments_data.isdigit():
        #     raise ValueError(f"Invalid header size or num of segments received: {header_and_segments_data}")

        if "," not in header_and_segments_data:
            print("[Error] Data format is incorrect. Missing ',' between header size and number of segments.")
            client_socket.send("ERROR_INVALID_FORMAT\n".encode('utf-8'))
            return None, None

        header_size, num_segments = header_and_segments_data.split(",")

        # המרת הנתונים למספרים והבקרה על תקינותם
        try:
            header_size = int(header_size)
            num_segments = int(num_segments)
        except ValueError:
            print("[Error] One of the values is not a valid integer.")
            client_socket.send("ERROR_INVALID_VALUES\n".encode('utf-8'))
            return None, None

        print(f"[Server] Received header size: {header_size} and num segments: {num_segments}")

        # שליחת ACK על קבלת המידע
        client_socket.send("ACK_HEADER_AND_SEGMENTS\n".encode('utf-8'))
        print("[Server] Sent acknowledgment for header size and number of segments.")

        return header_size, num_segments

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
    string_buffer = ""  # Temporary buffer to store message contents
    unordered_buffer = {}  # Buffer to store out-of-order messages

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((host, port))
        server_socket.listen(5)
        print(f"Server started on {host}:{port}. Waiting for connections...")

        last_acknowledged = -1
        last_message_received = None  # To keep track of the last message number

        while True:  # External loop to handle new connections
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")

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

                print("Requesting header size and num segments from client...")
                header_size, num_segments = receive_header_size_and_num_segment(client_socket)
                if header_size is None:
                    print("Failed to receive header size and num segments. Closing connection.")
                    client_socket.close()
                    break  # Exit if header size not received

                print(f"Header size received successfully: {header_size} and num segments : {num_segments}")

                # Read message from the client
                while True:
                    try:
                        highest_sequence_in_batch = last_acknowledged  # Track the highest sequence in the current batch
                        part_count = 0  # Track how many parts have been processed in this batch
                        window_size = 4  # TODO: the window size can be adjusted by user input
                        string_buffer = ""  # Temporary buffer to store message contents
                        unordered_buffer = {}  # Buffer to store out-of-order messages

                        while part_count < window_size:  # Receive up to `window_size` messages in this batch
                            try:
                                client_socket.settimeout(20)  # Set a timeout to avoid hanging
                                data = client_socket.recv(BUFFER_SIZE).decode('utf-8')  # Receive data

                                if not data:
                                    print("Client disconnected or no more data to receive.")
                                    break  # Exit loop if the client sends no more data

                                print(f"Received raw data: {data}")
                                string_buffer += data  # Append received data to buffer

                                # Process complete messages in the buffer
                                while "\n" in string_buffer:
                                    message, string_buffer = string_buffer.split("\n", 1)  # Split at the first newline
                                    if message.strip():  # Ignore empty messages
                                        print(f"Processing message: {message.strip()}")

                                        # Extract header and payload
                                        header = message[:header_size]
                                        payload = message[header_size:header_size + max_msg_size]
                                        print(f"Parsed message -> Header: {header}, Payload: {payload}")

                                        # Parse sequence number from the header
                                        try:
                                            sequence_number = int(header.strip())
                                            print(f"Sequence number extracted: {sequence_number}")
                                        except ValueError:
                                            print("Error: Invalid header received. Skipping this message.")
                                            continue  # Skip invalid messages

                                        # Handle in-order and out-of-order messages
                                        if sequence_number == last_acknowledged + 1:
                                            print(f"Message {sequence_number} received in order.")
                                            #fixme פה החבילה האחרונה נעצרת
                                            last_acknowledged = sequence_number  # Update the last acknowledged in-order message
                                            highest_sequence_in_batch = max(highest_sequence_in_batch, sequence_number)

                                            # Check if we can process buffered out-of-order messages
                                            while last_acknowledged + 1 in unordered_buffer:
                                                print(f"Message {last_acknowledged + 1} now in order.")
                                                last_acknowledged += 1
                                                del unordered_buffer[last_acknowledged]
                                                highest_sequence_in_batch = max(highest_sequence_in_batch,
                                                                                last_acknowledged)

                    #fixme פה היה הבדיקה האחרונה
                                        else:
                                            if sequence_number not in unordered_buffer:
                                                print(f"Message {sequence_number} received out of order. Storing in buffer.")
                                                unordered_buffer[sequence_number] = payload
                                            else:
                                                print(f"Duplicate message {sequence_number} received. Ignoring.")

                                        part_count += 1  # Increment the count of messages in the batch

                            except socket.timeout:
                                print("Timeout occurred while waiting for client data.")
                                break  # Exit batch processing on timeout

                        # After processing all messages in the current batch
                        print(f"Processed {part_count} message(s) in the current batch.")

                        # Debugging: print all possible ACKs
                        possible_acks = list(range(last_acknowledged + 1))
                        print(f"Possible ACKs (up to current batch): {possible_acks}")

                        # After receiving the batch, send an ACK for the highest sequence number in this batch
                        ack = f"ACK{highest_sequence_in_batch}".ljust(header_size)
                        client_socket.send(ack.encode('utf-8'))
                        print(f"Sent cumulative ACK: {highest_sequence_in_batch}")

                        # Check if this is the last message
                        if last_acknowledged == num_segments - 1:  # אם קיבלנו את ההודעה האחרונה
                            print("Last message received. Sending FINAL_ACK.")
                            time.sleep(1)  # זמן המתנה קטן לפני שליחת ה-FINAL_ACK
                            final_ack = "FINAL_ACK"
                            client_socket.send(final_ack.encode('utf-8'))  # Send FINAL_ACK
                            print("[Server] Sent FINAL_ACK. Closing connection.")
                            break  # Exit the loop after sending the final acknowledgment

                        if part_count < window_size and len(string_buffer) == 0:
                            print("No more parts expected. Exiting loop early.")
                            final_ack = "FINAL_ACK"
                            client_socket.send(final_ack.encode('utf-8'))  # Notify client explicitly
                            print("[Server] Sent FINAL_ACK. Closing connection.")
                            break

                    except ConnectionResetError:
                        print("Connection was reset by the client.")
                        break
                    except Exception as e:
                        print(f"Unexpected error while processing client message: {e}")
                        break

            except ConnectionResetError:
                print("Connection was reset by the client.")
            finally:
                client_socket.close()
                print(f"Connection with {client_address} closed.")


if __name__ == "__main__":
    start_server()
