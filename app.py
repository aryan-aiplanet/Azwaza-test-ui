import asyncio
import websockets
import json
import streamlit as st

# WebSocket and audio chunk settings
speech_super_base_url = "wss://speech-eval.aimarketplace.co/api/speech-evaluation/" 
tts_base_url = "wss://speech-eval.aimarketplace.co/api/text-to-speech/"
authorization_header = {"Authorization": "Api-Key 31c4b5dd307b6fadc8cd5043fb82d984"}
chunk_size = 1024

# Function to handle Speech Super WebSocket communication
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
                # st.write(f"Sent audio chunk of size {len(audio_chunk)} bytes")
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

# Function to handle Text-to-Speech WebSocket communication
async def text_to_speech(reference_text):
    try:
        async with websockets.connect(tts_base_url, extra_headers=authorization_header) as ws:
            st.write("Connected to Text-to-Speech WebSocket server.")

            # Send the text message
            await ws.send(json.dumps({"text": reference_text, "accent": "US", "gender": "MALE"}))
            st.write(f"Sent text for TTS: {reference_text}")

            # Receive and play the audio chunks
            while True:
                try:
                    response = await ws.recv()
                    data = json.loads(response)

                    word = data.get('word')
                    audio_base64 = data.get('audio')

                    # Display word and audio status
                    if word and audio_base64:
                        st.write(f"Received word: {word}, audio length: {len(audio_base64)}")
                except websockets.ConnectionClosed:
                    st.write("Text-to-Speech connection closed by server.")
                    break
    except Exception as e:
        st.error(f"An error occurred: {e}")

# Sidebar for navigation
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
            st.write("Processing...")

            # Run the WebSocket communication for Text-to-Speech
            asyncio.run(text_to_speech(tts_text))
        else:
            st.warning("Please enter some text to convert to speech.")
