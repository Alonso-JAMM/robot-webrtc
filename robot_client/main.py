import logging
import asyncio
import threading
from robot_client import config
from robot_client.socketio_client import SocketClient, ClientNameSpace

# Setting up the logger of the application
logger = logging.getLogger("main")
logger.setLevel(config.logging_config["level"])
# console handler
ch = logging.StreamHandler()
ch.setLevel(config.logging_config["level"])
# file handler
fh = logging.FileHandler(config.logging_config["filename"])
fh.setLevel(config.logging_config["level"])
# attach handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)
# create formatter
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(threadName)s - %(funcName)s - %(levelname)s --- %(message)s")
ch.setFormatter(formatter)
fh.setFormatter(formatter)


def arduino_connection():
    """Here, we connect to the socketio server as a listener that is only interested in data that will control the
        arduino"""
    # creating a loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("Initiating arduino stuff")
    my_namespace = ClientNameSpace(name="listener")
    my_client = SocketClient(namespace=my_namespace)
    asyncio.run(my_client.connect(config.socketio_options["URL"]))


def camera_connection():
    """ Here, we connect to the socketio server with the intention of creating a peer connection with viewers and
        stream video to them """
    # creating a loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("Initiating camera stuff")
    my_namespace = ClientNameSpace(name="bot1")
    my_client = SocketClient(namespace=my_namespace)
    asyncio.run(my_client.connect(config.socketio_options["URL"]))


def main():
    logger.info("Logging level " + str(logger.handlers[0].level))
    logger.info("The application has been initiated")
    logger.info("Now trying to connect to the socket.io server")

    # Setting up the threads
    arduino_thread = threading.Thread(target=arduino_connection)
    camera_thread = threading.Thread(target=camera_connection)
    # Starting the threads
    arduino_thread.start()
    camera_thread.start()


if __name__ == "__main__":
    main()
