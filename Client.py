import socket
import time

from api import BUFFER_SIZE, DEFAULT_SERVER_HOST, DEFAULT_SERVER_PORT, HEADER_SIZE
import math

def create_header(sequence_number, header_size):
    """
    יוצר Header שמכיל רק את המספר הסידורי.
    """
    sequence_number_str = f"{sequence_number:0{header_size}d}"  # מספר סידורי בגודל קבוע
    return sequence_number_str


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

        # Get all parameters (message, window size, timeout)
        parameters = get_all_client_parameters()
        message = parameters["message"]
        window_size = parameters["window_size"]
        timeout = parameters["timeout"]  # Retrieve the timeout value

        # Calculate payload size
        payload_size = max_msg_size_from_server
        print(f"Payload size set to: {payload_size}")
        if payload_size <= 0:
            print("Error: HEADER_SIZE is larger than or equal to MAX_MSG_SIZE. Aborting.")
            return

        total_message_size = len(message)
        num_segments = math.ceil(total_message_size / max_msg_size_from_server)
        header_size = len(str(num_segments))  # ספרות למספר סידורי

        try:
            # קבלת כל הנתונים מהשרת
            response_data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            print(f"The server's message: {response_data}")
            responses = response_data.split("\n")  # פיצול הודעות לפי '\n'

            # עיבוד ההודעות שהתקבלו
            ack_received = False  # משתנה לבדיקת אישור קבלת גודל ההדר

            for response in responses:
                response = response.strip()
                if response == "GET_HEADER_SIZE_AND_NUM_SEGMENTS_AND_WINDOW_SIZE":
                    print("[Client] Server requested header size and number of segments and window size.")

                    # חישוב ושליחת גודל Header
                    #header_size = 4  # לדוגמה
                    print(f"Calculated : header size: {header_size} +  num segments: {num_segments} + window_size: {window_size}")

                    try:
                        data_to_send = f"{header_size},{num_segments},{window_size}\n"  # שולחים את המידע מופרד בפסיק
                        client_socket.send(data_to_send.encode('utf-8'))
                        print(f"[Client] Sent header size : {header_size} and num segments :{num_segments} and window_size : {window_size}")
                    except Exception as e:
                        print(f"[Error] Failed to send parameters: {e}")
                        print("[Error] Reconnecting to server...")
                        try:
                            client_socket.close()
                        except Exception as e:
                            print(f"[Warning] Failed to close socket: {e}")
                        exit(1)

                    # קבלת ACK מהשרת
                    try:
                        ack_response = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
                        if ack_response == "ACK_HEADER_AND_SEGMENTS":
                            print("[Client] Server acknowledged header size and num of segment.")
                            ack_received = True
                        else:
                            print(f"[Error] Unexpected response from server: {ack_response}")
                            exit(1)
                    except Exception as e:
                        print(f"[Error] Failed to receive ACK: {e}")
                        exit(1)
                elif response:
                    print(f"[Error] Unexpected message from server: {response}")
                    exit(1)

            if not ack_received:
                print("[Error] ACK_HEADER_AND_SEGMENTS not received. Reconnecting...")
                try:
                    client_socket.close()
                except Exception as e:
                    print(f"[Warning] Failed to close socket: {e}")

                # התחברות מחדש
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    client_socket.connect((host, port))
                    print("Reconnected to the server. Retrying header size and num of segment transmission...")
                    client_socket.send(f"{header_size}".encode('utf-8'))
                    print(f"Sent fixed header size after reconnecting: {header_size} and num of segment: {num_segments}")
                except Exception as e:
                    print(f"[Critical] Failed to reconnect or send header size and num of segment. Exiting. Error: {e}")
                    exit(1)

        except Exception as e:
            print(f"Failed to send header size and num of segment. Exiting. Error: {e}")
            exit(1)  # סיום התוכנית במקרה של כשל

        # Split the message into parts
        parts = [message[i:i + payload_size] for i in range(0, total_message_size, payload_size)]
        print(f"Total message size: {total_message_size}")
        print(f"Message split into {len(parts)} parts.")
        print(f"num_segments: {num_segments}")


        window_start = 0
        unacknowledged = set(range(len(parts)))  # Track unacknowledged parts
        last_acknowledged = -1  # Start with -1 because no parts have been acknowledged yet

        # Precompute headers for all parts
        print("*start sending the message")
        headers = {
            i: create_header(sequence_number=i, header_size=header_size)
            for i in range(len(parts))
        }

        # Sliding window mechanism with timeout
        try:
            # הלקוח שולח את ההודעות לפי גודל החלון ואז מחכה ל-ACK עבור כל ה-BATCH.
            while unacknowledged:
                window_end = min(window_start + window_size, len(parts))
                print(f"Current window: {window_start} to {window_end - 1}")

                # הכנת ההודעות לשליחה אחת אחרי השנייה
                for i in range(window_start, window_end):
                    if i in unacknowledged:
                        header = headers[i]
                        full_message = header + parts[i] + "\n"
                        print(
                            f"[Debug] Prepared message Part {i}/{len(parts)}: {full_message} (Size: {len(full_message)} bytes)")

                        try:
                            # שולחים את ההודעה אחת אחרי השנייה
                            client_socket.send(full_message.encode('utf-8'))
                            print(f"[Client] Sent message: {full_message}")
                        except Exception as e:
                            print(f"[Error] Failed to send message: {e}")
                            raise

                # התחל טיימר לחכות ל-ACK
                timer_start = time.time()
                ack_received = False
                final_ack_received = False  # Flag to check if FINAL_ACK is received

                # המתנה ל-ACK עבור כל ההודעות שב-BATCH
                while time.time() - timer_start < timeout:
                    try:
                        client_socket.settimeout(timeout - (time.time() - timer_start))
                        response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                        print(f"this is the response: {response}")

                        if response.startswith("ACK"):
                            ack_num = int(response.replace("ACK", "").strip())
                            print(f"[ACK] Received ACK for message: {ack_num}")
                            ack_received = True

                            # בדוק אם זה ה-ACK עבור ההודעה האחרונה
                            if ack_num == num_segments - 1:
                                print("[Client] Last ACK received. Waiting for FINAL_ACK from server.")

                                # המתן לקבלת FINAL_ACK
                                while True:
                                    #todo timeoot
                                    response = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                                    if response == "FINAL_ACK":
                                        print("[Client] Received FINAL_ACK from server. Closing connection.")
                                        final_ack_received = "ACK_FINAL_RECEIVED"
                                        client_socket.send(final_ack_received.encode('utf-8'))  # Notify client explicitly
                                        print(f"[Client] Sent ACK_FINAL_RECEIVED to server + {final_ack_received}")
                                        time.sleep(2)
                                        break  # Exit the loop when the server sends the final ACK
                                    else:
                                        print(f"[Error] Unexpected response: {response}. Retrying...")

                            # עיבוד ACK עבור כל המסרים
                            for seq in range(window_start, ack_num + 1):
                                if seq in unacknowledged:
                                    unacknowledged.discard(seq)
                            window_start = ack_num + 1
                            break  # Exit timeout loop on successful ACK

                        else:
                            print(f"[Error] Unexpected response from server: {response}")

                    except socket.timeout:
                        print(f"[Timeout] No ACK received within {timeout} seconds.")
                        break
                    except (ValueError, ConnectionResetError) as e:
                        print(f"[Error] Acknowledgment processing failed: {e}. Retrying unacknowledged parts.")
                        break

                    else:
                        print("[Error] Did not receive final ACK. Closing connection.")

                    client_socket.close()
                    print("Connection closed.")

                else:
                    print("[Error] Did not receive final ACK. Closing connection.")

                if not ack_received:
                    if window_start >= len(parts):
                        print("[Client] Final batch sent. No more messages to retry.")
                        break
                    else:
                        print(f"[Retrying] Retrying unacknowledged parts in window: {window_start} to {window_end - 1}")

                        # שליחת ההודעות מחדש עבור החלקים שלא אושרו
                        batch_messages = []
                        for i in range(window_start, window_end):
                            if i in unacknowledged:
                                header = headers[i]  # Use precomputed header
                                full_message = header + parts[i]
                                batch_messages.append(full_message)
                                print(
                                    f"[Debug] Prepared message Part {i + 1}/{len(parts)}: {full_message} (Size: {len(full_message)} bytes)")

                        if batch_messages:
                            # Join messages into a batch with '\n'
                            batch_data = "".join(batch_messages) + "\n"
                            print(f"[Debug] Complete batch to send: {batch_data}")

                            try:
                                client_socket.send(batch_data.encode('utf-8'))
                                print(f"[Client] Sent batch successfully: {batch_data}")
                            except Exception as e:
                                print(f"[Error] Failed to send batch: {e}")
                                raise

        finally:
            if not unacknowledged:
                print("All messages sent and acknowledged.")
            else:
                print("Not all messages were acknowledged.")

            try:
                # רק אם החיבור עדיין פתוח, ננסה לסגור אותו
                if not client_socket._closed:
                    print("Closing the connection.")
                    client_socket.shutdown(socket.SHUT_WR)  # Graceful shutdown
                    client_socket.close()
                    print("Connection closed gracefully.")
            except Exception as e:
                print(f"[Error] Failed to close the connection: {e}")



if __name__ == "__main__":
    start_client()