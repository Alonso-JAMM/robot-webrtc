import logging

# Video options passed to ffmpeg
# They are used by aiortc
video_options = {
    "framerate": "30",
    "video_size": "320x192"
}

# Socketio options used to connect to the server
socketio_options = {
    "URL": "http://10.0.0.5:8082"
}

# Devices used by the application
devices = {
    "camera": "/dev/video0",
    "arduino": "/dev/ttyACM0",
    "ardduino_baud_rate": "38400"

}

# Configuration used by the logger of the application
logging_config = {
    "level": logging.DEBUG,
    "filename": "example.log"
}
