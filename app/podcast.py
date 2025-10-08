from os import path
import os

from .podcastfy.client import generate_podcast, process_content


# Define a custom conversation config for a tech debate podcast
podcast_config = {
    'roles_person1': ['Economist', 'Thought Leader', 'Businessman', 'Technologist'], 
    'roles_person2': ['Economist', 'Thought Leader', 'Businessman', 'Technologist'], 
    'dialogue_structure': ['Topic Introduction', 'Summary of Key Points', 'Discussions/Conclusions'],
    'user_instructions': ['Summarizes information by breaking it down into themes and key points', 'No Filler'],  
    'creativity': 0.5
}

def is_file_empty(file_path):
    """
    Checks if a file (text or MP3) is empty.

    Args:
        file_path (str): The path to the file.

    Returns:
        bool: True if the file is empty or does not exist, False otherwise.
    """
    try:
        # Get the size of the file in bytes
        file_size = os.path.getsize(file_path)
        # If the size is 0, the file is considered empty
        return file_size == 0
    except FileNotFoundError:
        # Handle cases where the file does not exist
        print(f"Error: File not found at {file_path}")
        return True  # Consider non-existent files as "empty" in this context

def generate_transcript(content):
        return process_content(text=content, 
                model_name="gemini-2.5-pro",
                generate_audio=False,
                conversation_config=podcast_config)

def generate_audio(filepath):
        generate_podcast(transcript_file=filepath, 
                        tts_model='gemini',
                        conversation_config=podcast_config)

def generate_pod(content):
        generate_podcast(text=content,
                        llm_model_name="gemini-2.5-pro", 
                        tts_model='gemini',
                        conversation_config=podcast_config)


# TEST            
if __name__ == "__main__":
    # service = access.gmail_authenticate()
    # content = access.create_podcast_content(service)

    # if content is not None:
    #     path = generate_transcript(content)
    #     generate_audio(path)

    transcript_filepath = "tmp/transcript.txt"
    audio_filepath = "tmp/podcast.mp3"
    root = path.dirname(path.abspath(__file__))
    print(root)
    if is_file_empty(transcript_filepath):
        print("yes, transcript is empty")
    if is_file_empty(audio_filepath):
        print("yes, audio is empty")

