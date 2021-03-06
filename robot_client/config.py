import logging

# Video options passed to ffmpeg
# They are used by aiortc
video_options = {
    "framerate": "30",
    "video_size": "320x192"
}

# janus options used to connect to the server
janus_options = {
    "URL": "http://10.0.0.5:8082",
    "room_video": 1234,
    "room_text": 1234
}

# Devices used by the application
devices = {
    "camera": {
        "location": "/dev/video0"
    },
    "arduino": {
        "location": "/dev/ttyACM0",
        "baud_rate": "38400",
        "read_timeout": "0.02"
    }
}

# Configuration used by the logger of the application
logging_config = {
    "level": logging.DEBUG,
    "filename": "example.log"
}

