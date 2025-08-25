import access
import os
from playsound import playsound

from podcastfy.client import generate_podcast, process_content


# Define a custom conversation config for a tech debate podcast
podcast_config = {
    'conversation_style': ['Engaging', 'Fast-paced', 'Enthusiastic', 'Educational'], 
    'roles_person1': ['Economist, Thought Leader, Businessman, Tech Enthusiast', "Main Summarizer"], 
    'roles_person2': 'None', 
    'dialogue_structure': ['Topic Introduction', 'Summary of Key Points', 'Discussions'], 
    'podcast_name': 'Daily Metis News', 
    'podcast_tagline': 'Keep up with Metis on tech and business', 
    'output_language': 'English', 
    'user_instructions': ['Summarizes news by breaking it down into key points', 'No Filler'],  
    'creativity': 0.75
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
                        longform=True,
                        conversation_config=podcast_config)


# TEST            
if __name__ == "__main__":
    service = access.gmail_authenticate()
    content = access.create_podcast_content(service)
    path = generate_transcript(content)
    generate_audio(path)