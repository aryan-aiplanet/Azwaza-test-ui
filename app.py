import asyncio
import websockets
import json
import streamlit as st
import base64
from pydub import AudioSegment
from pydub.playback import play
import io
import threading

# WebSocket and audio chunk settings
speech_super_base_url = st.secrets["websocket"]["speech_super_base_url"]
tts_base_url = st.secrets["websocket"]["tts_base_url"]
authorization_header = {"Authorization": st.secrets["websocket"]["authorization_key"]}
chunk_size = 1024

# Speech Super WebSocket function
async def send_audio_and_get_response(reference_text, audio_data):
    try:
        async with websockets.connect(speech_super_base_url, extra_headers=authorization_header) as ws:
            st.write("Connected to WebSocket server.")

            # Send reference text
            await ws.send(json.dumps({"reference_text": reference_text}))
            st.write(f"Sent reference text: {reference_text}")

            # Send audio in chunks
            audio_offset = 0
            while audio_offset < len(audio_data):
                audio_chunk = audio_data[audio_offset:audio_offset + chunk_size]
                await ws.send(audio_chunk)
                audio_offset += chunk_size

            # Send stop signal
            await ws.send(b"STOP")
            st.write("Sent stop signal.")

            # Get the first response
            response = await ws.recv()
            st.write(f"Received response: {response}")

            # Get the final response
            while True:
                try:
                    response = await ws.recv()
                    st.write(f"Received final response: {response}")
                except websockets.exceptions.ConnectionClosed:
                    st.write("Connection closed by server.")
                    break
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Text-to-Speech WebSocket function
async def send_text_and_receive_audio(text):
    message = {
        "text": text,
        "accent": "US",
        "gender": "FEMALE",
    }

    try:
        # Establish the WebSocket connection
        async with websockets.connect(tts_base_url, extra_headers=authorization_header) as websocket:
            st.write("Connected to WebSocket server.")
            
            try:
                # Send the message with text, accent, and gender
                await websocket.send(json.dumps(message))
                st.write(f"Sent reference text: {message['text']}")
                
                while True:
                    try:
                        # Receive audio chunks or status message
                        response = await websocket.recv()
                        data = json.loads(response)

                        status = data.get('status')
                        
                        if status == "error":
                            # Handle the error case
                            error_message = data.get('error', 'Unknown error occurred.')
                            st.write(f"Error received: {error_message}")
                            break  # Stop further processing if an error occurs
                        
                        # Continue processing if status is not "error"
                        word = data.get('word')
                        audio_base64 = data.get('audio')

                        # Check if all required fields are present
                        if word and audio_base64:
                            # Decode the audio from base64 to binary
                            audio_data = base64.b64decode(audio_base64)
                            st.write(f"Received word: {word}, Audio data length: {len(audio_data)}, Status: {status}")

                            # Play the audio in real-time using pydub
                            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="wav")
                            play(audio_segment)  # This plays the audio in real-time
                            
                        else:
                            st.write("Incomplete data received:", data)

                    except websockets.ConnectionClosedError as e:
                        st.write(f"Connection closed with error: {e}")
                        break
                    
                    except Exception as e:
                        st.write(f"Error processing the received message: {e}")

            except websockets.ConnectionClosedError as e:
                st.write(f"Connection closed unexpectedly: {e}")

            except Exception as e:
                st.write(f"Error sending or receiving WebSocket messages: {e}")

    except websockets.InvalidURI as e:
        st.write(f"Invalid WebSocket URI: {e}")

    except websockets.InvalidHandshake as e:
        st.write(f"Invalid handshake: {e}")

# Function to run WebSocket connection in a separate thread (for Text-to-Speech)
def run_websocket(text):
    asyncio.run(send_text_and_receive_audio(text))

# Streamlit sidebar for navigation
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", ["Speech Super", "Text-to-Speech"])

if selection == "Speech Super":
    # Speech Super Functionality
    st.title("Speech Super Evaluation")

    # Input field for reference text
    reference_text = st.text_input("Enter the reference text")

    # File uploader for .wav audio file
    audio_file = st.file_uploader("Upload a .wav audio file", type=["wav"])

    # Submit button for Speech Super
    if st.button("Start Evaluation"):
        if reference_text and audio_file:
            audio_data = audio_file.read()  # Read the audio file data
            st.write("Processing...")

            # Run the WebSocket communication in an asyncio event loop
            asyncio.run(send_audio_and_get_response(reference_text, audio_data))
        else:
            st.warning("Please provide both reference text and a .wav audio file.")

elif selection == "Text-to-Speech":
    # Text-to-Speech Functionality
    st.title("Text-to-Speech")

    # Input field for the text to convert to speech
    tts_text = st.text_input("Enter the text to convert to speech")

    # Submit button for Text-to-Speech
    if st.button("Start Text-to-Speech"):
        if tts_text:
            # Run WebSocket connection in a separate thread for real-time TTS
            thread = threading.Thread(target=run_websocket, args=(tts_text,))
            thread.start()
        else:
            st.warning("Please enter some text to convert to speech.")
