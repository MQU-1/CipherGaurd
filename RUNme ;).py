import threading
import webbrowser

from cipherguard import create_app

HOST = "127.0.0.1"
PORT = 5000
ADDRESS = "http://{}:{}".format(HOST, PORT)

app = create_app()


if __name__ == "__main__":
    print("CipherGuard is running at " + ADDRESS)
    print("Sign in as admin / AdminCipherGuard1! to reach the audit trail.")
    print("Press Ctrl+C in this window to stop the server.")
    threading.Timer(1.2, webbrowser.open, [ADDRESS]).start()
    app.run(host=HOST, port=PORT)
