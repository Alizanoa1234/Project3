# import socket
#
# API_BUFFERSIZE = 65536  # גודל הבופר להודעות
# MAX_MSG_SIZE = 400  # גודל הודעה כולל (payload + header)
# HEADER_SIZE = 10  # גודל ה-header הקבוע
#
# def start_server():
#     host = '127.0.0.1'
#     port = 9999
#
#     with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
#         server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#         server_socket.bind((host, port))
#         server_socket.listen(5)
#         print(f"Server started on {host}:{port}. Waiting for connections...")
#
#         last_acknowledged = -1
#         buffer = {}
#
#         while True:  # לולאה חיצונית להאזנה לחיבורים חדשים
#             client_socket, client_address = server_socket.accept()
#             print(f"Connection established with {client_address}")
#
#             try:
#                 while True:  # לולאה פנימית להודעות מאותו לקוח
#                     # קריאת הודעה או בקשה מהלקוח
#                     message = client_socket.recv(API_BUFFERSIZE).decode('utf-8')
#                     if not message:
#                         print("Client disconnected.")
#                         break  # יציאה מהלולאה אם הלקוח סגר את החיבור
#
#                     print(f"Received message: {message}")
#
#                     if message == "GET_MAX_MSG_SIZE":
#                         # שליחת גודל הודעה מקסימלי ללקוח
#                         response = str(MAX_MSG_SIZE)
#                         client_socket.send(response.encode('utf-8'))
#                         print(f"Sent max message size: {response}")
#                         continue  # המשך להאזנה להודעות נוספות
#
#                     # טיפול בהודעות רגילות
#                     header = message[:HEADER_SIZE]
#                     payload = message[HEADER_SIZE:]
#                     sequence_number = int(header[:4].strip())
#
#                     print(f"Received: Sequence Number: {sequence_number}, Payload: {payload}")
#
#                     # ניהול ACK ושמירה על הסדר
#                     if sequence_number == last_acknowledged + 1:
#                         print(f"Message {sequence_number} received in order.")
#                         last_acknowledged = sequence_number
#
#                         while last_acknowledged + 1 in buffer:
#                             print(f"Message {last_acknowledged + 1} now in order.")
#                             last_acknowledged += 1
#                             del buffer[last_acknowledged]
#                     else:
#                         print(f"Message {sequence_number} received out of order. Storing in buffer.")
#                         buffer[sequence_number] = payload
#
#                     # שליחת ACK
#                     ack = f"ACK{last_acknowledged}".ljust(HEADER_SIZE)
#                     client_socket.send(ack.encode('utf-8'))
#                     print(f"Sent ACK: {last_acknowledged}")
#
#             except ConnectionResetError:
#                 print("Connection was reset by the client.")
#             finally:
#                 client_socket.close()
#                 print(f"Connection with {client_address} closed.")
#
#
# if __name__ == "_main_":
#      start_server()

import socket


def server(host: str, port: int) -> None:
    # הגדרת פרמטרים לשרת
    host = '127.0.0.1'  # הכתובת המקומית
    port = 12345  # מספר פורט (ניתן לשנות)

    # יצירת אובייקט socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((host, port))  # קישור השרת לכתובת ולפורט
        server_socket.listen(5)  # השרת מאזין עד 5 חיבורים בו-זמנית
        threads = []
        print(f"Server started on {host}:{port}. Waiting for connections...")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")

            # קריאת הודעה מהלקוח
            message = client_socket.recv(1024).decode('utf-8')
            print(f"Received message: {message}")

            # שליחת תשובה ללקוח
            response = "Message received"
            client_socket.send(response.encode('utf-8'))

            # סגירת חיבור עם הלקוח
            client_socket.close()
            print(f"Connection with {client_address} closed.")


if __name__ == "_main_":
    start_server()