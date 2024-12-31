import socket

# הגדרות בסיסיות
api_buffersize = 65536  # גודל הבופר להודעות
header_size = 10  # גודל ה-header הקבוע

def create_header(sequence_number, payload_size):
    """
    יוצר header הכולל מספר סידורי וגודל ה-payload.
    """
    return f"{sequence_number:04}{payload_size:04}".ljust(header_size)

def read_config_file(filename='config.txt'):
    """
    קורא את הפרמטרים מקובץ קונפיגורציה ומחזיר מילון של פרמטרים.
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
        print("Configuration file not found.")
    except Exception as e:
        print(f"Error reading configuration file: {e}")
    return None

def get_message_from_file(filename='config.txt'):
    """
    קורא הודעה מתוך קובץ הקונפיגורציה.
    """
    try:
        with open(filename, 'r') as file:
            for line in file:
                if line.startswith("message"):
                    return line.split(":", 1)[1].strip()
        print("Message not found in file.")
    except FileNotFoundError:
        print("Configuration file not found.")
    except Exception as e:
        print(f"Error reading configuration file: {e}")
    return None

def get_message_from_user():
    """
    מבקש מהמשתמש להזין הודעה, ומבטיח שהיא לא תהיה ריקה.
    """
    message = input("Enter the message to send: ")
    while not message.strip():
        print("Message cannot be empty. Please enter a valid message.")
        message = input("Enter the message to send: ")
    return message

def choose_message_source():
    """
    מאפשר למשתמש לבחור את מקור ההודעה (קובץ או קלט ידני).
    """
    source = input("Enter message source (file/user): ").strip().lower()
    if source not in ["file", "user"]:
        print("Invalid input. Defaulting to 'user'.")
        source = "user"
    return source

def start_client():
    host = '127.0.0.1'
    port = 9999

    # קריאת פרמטרים מקובץ הקונפיגורציה
    config = read_config_file()
    if config is None:
        print("Failed to load configuration.")
        exit(1)

    max_msg_size = int(config.get('maximum_msg_size', 400))


    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((host, port))
        print("Connected to server.")

        # בחירת מקור ההודעה
        source = choose_message_source()
        if source == "file":
            message = get_message_from_file()
            if not message:
                print("Falling back to user input.")
                message = get_message_from_user()
        else:
            message = get_message_from_user()

        print(f"Message to send: {message}")

        # שליחת בקשה לגודל הודעה מקסימלי
        request = "GET_MAX_MSG_SIZE"
        client_socket.send(request.encode('utf-8'))
        max_msg_size = int(client_socket.recv(api_buffersize).decode('utf-8'))
        print(f"Received max message size from server: {max_msg_size}")

        # חישוב גודל ה-payload
        payload_size = max_msg_size - header_size
        if payload_size <= 0:
            print("Error: HEADER_SIZE is larger than or equal to max_msg_size.")
            return

        # שליחת הודעה לשרת (פיצול במקרה של גודל הודעה גדול)
        if len(message) > payload_size:
            print("Message exceeds max payload size, splitting into parts.")
            parts = [message[i:i+payload_size] for i in range(0, len(message), payload_size)]
            print(f"Total parts to send: {len(parts)}")  # הדפסת מספר החלקים
            for i, part in enumerate(parts):
                header = create_header(i, len(part))
                full_message = header + part
                print(f"Part {i + 1}/{len(parts)}: {len(part)} bytes, Content: {part}")  # פרטים על כל חלק
                client_socket.send(full_message.encode('utf-8'))
        else:
            header = create_header(0, len(message))
            full_message = header + message
            print(f"Sending message: {full_message}")
            client_socket.send(full_message.encode('utf-8'))

        # קבלת תשובה מהשרת
        response = client_socket.recv(api_buffersize).decode('utf-8')
        print(f"Received response from server: {response}")

if __name__ == "__main__":
    start_client()
