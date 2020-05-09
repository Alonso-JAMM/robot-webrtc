import logging
import asyncio
import threading
from robot_client import config
from robot_client.janus_client import JanusSession, camera_stream, TextClient
#from robot_client.arduino_controller import ArduinoSerial

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
    # Connecting to the arduino
    # creating a loop for the thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    logger.info("Initiating arduino stuff")
    #TODO Create a Data Channel connection to send and receive data if possible

class TextConnection(threading.Thread):
    def __init__(self, stop_signal):
        super().__init__()
        logger.info("Initiating text connection")
        self.url = config.janus_options["URL"]
        self.room = config.janus_options["room_text"]
        self.session = JanusSession(self.url)   # Having two different sessions Good or Bad?
        self.loop = None
        self.signal = stop_signal
        self.text_client = TextClient(self.session, self.room)

    def run(self):
        logger.info("Beginning text room connection")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(
            self.text_client.create()
        )
        self.loop.run_forever()

    def clean(self):
        """
        CLoses peer connection before exiting
        """
        logger.info("Closing text room connection")
        asyncio.set_event_loop(self.loop)
        self.loop.stop()
        # Wait unitl the loop is stoped
        while self.loop.is_running():
            pass
        self.loop.run_until_complete(self.session.destroy())
        self.signal.set()


class CameraConnection(threading.Thread):
    def __init__(self, stop_signal):
        super().__init__()
        logger.info("Initiating camera connection")
        self.url = config.janus_options["URL"]
        self.room = config.janus_options["room_video"]
        self.camera_opts = config.video_options
        self.session = JanusSession(self.url)
        self.loop = None
        self.signal = stop_signal

    def run(self):
        logger.info("Beginning video connection")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(
            camera_stream(session=self.session, room=self.room,
                          camera_options=self.camera_opts)
        )
        self.loop.run_forever()

    def clean(self):
        """
        Closes peer connection before exiting
        """
        logger.info("Closing camera connection")
        asyncio.set_event_loop(self.loop)
        self.loop.stop()
        # We need to wait until the loop is stoped in order to continue
        while self.loop.is_running():
            pass
        self.loop.run_until_complete(self.session.destroy())
        self.signal.set()


def main():
    logger.info("Logging level " + str(logger.handlers[0].level))
    logger.info("The application has been initiated")

    text_signal = threading.Event()
    text_thread = TextConnection(text_signal)
    text_thread.start()

    camera_signal = threading.Event()
    camera_thread = CameraConnection(camera_signal)
    camera_thread.start()
    try:
        camera_thread.join()
        text_thread.join()
    except (Exception, KeyboardInterrupt):
        pass
    finally:
        camera_thread.clean()
        text_thread.clean()
        camera_signal.wait()
        text_signal.wait()


if __name__ == "__main__":
    device = config.devices["arduino"]["location"]
    baud_rate = config.devices["arduino"]["baud_rate"]
    #arduino = ArduinoSerial(device, baud_rate)
    main()
