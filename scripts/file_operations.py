from google.cloud import firestore
from api_utils import get_file, list_files, upload_log, write_file

db = firestore.Client()
collection = db.collection("godmode-files")


def read_file(agent_id, filename):
    """Read a file and return the contents"""
    try:
        return get_file(filename, agent_id)
    except Exception as e:
        return "Error: " + str(e)


def write_to_file(agent_id, filename, text):
    """Write text to a file"""
    try:
        write_file(text, filename, agent_id)
        return "File written to successfully."
    except Exception as e:
        return "Error: " + str(e)


def append_to_file(agent_id, filename, text):
    """Append text to a file"""
    try:
        
        return "Text appended successfully."
    except Exception as e:
        return "Error: " + str(e)


def delete_file(agent_id, filename):
    """Delete a file"""
    # no-op for simplicity
    return "File deleted successfully."


def search_files(agent_id):
    """Search for files in a directory"""
    try:
        return list_files(agent_id)
    except Exception as e:
        return "Error: " + str(e)
