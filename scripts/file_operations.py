import os
import os.path
from google.cloud import firestore

db = firestore.Client()
collection = db.collection("godmode-files")


def read_file(agent_id, filename):
    """Read a file and return the contents"""
    try:
        content = (
            collection.document(agent_id + "/" + filename).get().to_dict()["content"]
        )
        return content
    except Exception as e:
        return "Error: " + str(e)


def write_to_file(agent_id, filename, text):
    """Write text to a file"""
    try:
        collection.document(agent_id + "/" + filename).set(
            {"content": text, "agent_id": agent_id}
        )
        return "File written to successfully."
    except Exception as e:
        return "Error: " + str(e)


def append_to_file(agent_id, filename, text):
    """Append text to a file"""
    try:
        content = (
            collection.document(agent_id + "/" + filename).get().to_dict()["content"]
        )
        collection.document(filename).set(
            {"content": content + "\n" + text, "agent_id": agent_id}
        )
        return "Text appended successfully."
    except Exception as e:
        return "Error: " + str(e)


def delete_file(agent_id, filename):
    """Delete a file"""
    try:
        collection.document(agent_id + "/" + filename).delete()
        return "File deleted successfully."
    except Exception as e:
        return "Error: " + str(e)


def search_files(agent_id):
    """Search for files in a directory"""
    try:
        files = collection.where("agent_id", "==", agent_id).get()
        file_list = []
        for file in files:
            file_list.append(file.id)
        return file_list
    except Exception as e:
        return "Error: " + str(e)
