import streamlit as st
from PIL import Image
import os
import json


def load_images_from_directory(directory):
    """
    Load all image paths from a directory.
    """
    supported_formats = [".png", ".jpg", ".jpeg"]
    return [os.path.join(directory, file) for file in os.listdir(directory) if file.lower().endswith(tuple(supported_formats))]


def load_json(json_path):
    """
    Load JSON data from the specified path.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return None
    except Exception as e:
        st.error(f"Error loading JSON: {e}")
        return None


def create_default_json(json_path):
    """
    Create a default JSON file with some initial structure.
    """
    default_data = {
        "description": "This is a default description.",
        "tags": []
    }
    save_json(default_data, json_path)
    return default_data


def save_json(json_data, save_path):
    """
    Save JSON data to the specified path.
    """
    print("saving to disk...")
    try:
        with open(save_path, "w", encoding="utf-8") as file:
            json.dump(json_data, file, indent=4)
        st.session_state['json_save_status'] = f"JSON saved successfully to {save_path}"
    except Exception as e:
        st.session_state['json_save_status'] = f"Error saving JSON: {e}"


def generate_json_for_image(image_filename):
    """
    Generate a JSON structure based on the image filename.
    """
    return {
        "description": f"Generated description for {image_filename}",
        "tags": ["auto-generated", "example"]
    }


def main():
    st.title("Image Directory Viewer and JSON Editor")

    # Directory input
    directory = st.sidebar.text_input("Enter the image directory path", value="../data/answer_key_images")

    # Initialize the save status in the session state
    if 'json_save_status' not in st.session_state:
        st.session_state['json_save_status'] = ""
    if 'last_saved_json' not in st.session_state:
        st.session_state['last_saved_json'] = ""

    # Display the save status message under the slider
    st.write(st.session_state['json_save_status'])

    # Load images from directory
    if os.path.isdir(directory):
        image_paths = load_images_from_directory(directory)

        if image_paths:
            st.sidebar.write(f"Found {len(image_paths)} images")

            # Select image to display - moved to the main panel
            selected_index = st.slider("Select Image", 0, len(image_paths) - 1, 0)
            selected_image_path = image_paths[selected_index]
            json_path = os.path.splitext(selected_image_path)[0] + ".json"
            st.session_state['last_saved_json'] = json.dumps(load_json(json_path), indent=4) if os.path.exists(json_path) else ""

            # Layout for image and JSON editor side by side
            col1, col2 = st.columns(2)

            with col1:
                # Display selected image
                image = Image.open(selected_image_path)
                st.image(image, caption=os.path.basename(selected_image_path), use_column_width=True)

                # Generate JSON button
                # if st.button("Generate JSON", key='generate_json_button'):
                #     generated_json = generate_json_for_image(os.path.basename(selected_image_path))
                #     st.session_state['last_saved_json'] = json.dumps(generated_json, indent=4)
                #     st.session_state['json_save_status'] = "Generated JSON and loaded into editor."

            with col2:
                # Load corresponding JSON (if exists), or create one if not found
                json_path = os.path.splitext(selected_image_path)[0] + ".json"
                json_data = load_json(json_path)
                if json_data is None:
                    json_data = create_default_json(json_path)

                # JSON Editor
                json_string = st.text_area('JSON Editor', value=st.session_state['last_saved_json'], height=300, label_visibility='collapsed', key='json_editor')

                # Save JSON
                if st.button("Save JSON", key='save_button'):
                    try:
                        # Validate and save JSON
                        edited_json = json.loads(json_string)
                        save_json(edited_json, json_path)
                        st.session_state['last_saved_json'] = json_string
                    except json.JSONDecodeError as e:
                        st.session_state['json_save_status'] = f"Invalid JSON: {e}"
        else:
            st.warning("No images found in the directory.")
    else:
        st.error("The specified directory does not exist.")


if __name__ == "__main__":
    main()
