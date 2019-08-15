# Introduction
This application is meant to be used to controll a small robot using python. By using socketio, it connects 
to an easyrtc server. With help of aiortc, it uses a camera in order to to create a video connection in which other 
easyrtc clients can watch the robot. The application also creates a separated thread that will listen to the socketio
messages and will use commands created by other easyrtc clients to control the bot. This separated thread will send 
write and read messages to the arduino. Since this process is relatively slow I decided to use a separated thread from
the one that is in charge of the video stream.

# Main Files in robot_client
1. **main** this file is the one that initiates connection to the server with two threads, one for listening commands
and the other is for doing the video streaming
2. **socketio_client** this file does all the socketio related stuff. Like connecting and listening to events.
It also do some of the stuff of setting peer connections.
3. **peer_connection** this file has the class that can be used to create peer connections with either video or not. 
The connection that uses video is the streamer whereas the the connection without video is the listener.
4. **config** is the main configuration file where all the settings for the application are found.