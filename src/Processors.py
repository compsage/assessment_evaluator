import os
import json
import urllib.request
import urllib.error
import concurrent.futures
from abc import ABC, abstractmethod
from SourceImage import SourceImage

class Processor(ABC):
    """
    Abstract base class for processing objects and managing prompts.
    """
    api_endpoint = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}",
        "Content-Type": "application/json"
    }

    def __init__(self, prompts_directory="../prompts"):
        """
        Initializes the Processor and loads prompt files from the specified directory.

        :param prompts_directory: Path to the directory containing .txt prompt files.
        """
        self.prompts = self._load_prompts(prompts_directory)

    def _load_prompts(self, directory):
        """
        Loads all .txt files from the given directory into a dictionary.

        :param directory: Path to the directory containing .txt files.
        :return: Dictionary with filenames (without extension) as keys and file content as values.
        """
        prompts = {}
        if not os.path.exists(directory):
            print(f"Directory '{directory}' does not exist. No prompts loaded.")
            return prompts

        for filename in os.listdir(directory):
            if filename.endswith(".txt"):
                filepath = os.path.join(directory, filename)
                with open(filepath, "r", encoding="utf-8") as file:
                    key = os.path.splitext(filename)[0]  # Remove the .txt extension
                    prompts[key] = file.read()

        return prompts

    @staticmethod
    def _process_chatgpt_response(raw_response):
        try:
            if not raw_response :
                print(f"Response from Chatgpt Empty: {raw_response}")
                return None
            if raw_response.startswith("```json"):
                raw_response = raw_response[len("```json"):].strip()
            if raw_response.endswith("```"):
                raw_response = raw_response[:-len("```")].strip()
            return json.loads(raw_response)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}\n raw_response: {raw_response}")
            return None
      
    @abstractmethod
    def process(self, *args, **kwargs):
        """
        Abstract method to process data. Must be implemented by subclasses.
        """
        pass

    def process(self, source_image, **kwargs):
        """
        Processes a SourceImage object. Placeholder for custom operations.

        :param source_image: The SourceImage object to process.
        :param kwargs: Additional parameters for processing (optional).
        :return: None
        """
        if not isinstance(source_image, SourceImage):
            raise ValueError("Input must be an instance of SourceImage.")

        print(f"Processing SourceImage: {source_image.get_metadata()}")
        print(f"Available Prompts: {list(self.prompts.keys())}")
        print(f"Additional parameters: {kwargs}")

    def call_genai_multi_threaded(self, images, key, max_workers=5):
        """
        Processes a list of SourceImage objects concurrently and extracts data from them.

        :param images: List of SourceImage objects to process.
        :param key: The key to fetch the prompt for processing.
        :param max_workers: Maximum number of concurrent workers (default is 5).
        :return: A dictionary where keys are image indices and values are the results or errors.
        """
        results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self.call_genai, image, key, **{}): image.get_source() for image in images
            }

            for future in concurrent.futures.as_completed(future_to_index):
                source = future_to_index[future]
                try:
                    result = future.result()
                    results[source] = result
                except Exception as e:
                    print(e)
                    print(f"error -> {source}")

        return results

    def call_genai(self, source_image, key, **kwargs):
        
        image_url_payload = None
        if source_image and not isinstance(source_image, SourceImage):
            raise ValueError("Input must be an instance of SourceImage.")
        elif source_image and isinstance(source_image, SourceImage):
            print(f"Sending {source_image.get_source()} to genai: {key}")
            image_url = f"data:image/jpeg;base64,{source_image.get_base64()}"
            image_url_payload = {
                    "type": "image_url",
                    "image_url": {
                        "url": image_url
                    }
                }

        if kwargs :
            formatted_template = self.prompts[key].format(**kwargs)
        else :
            formatted_template = self.prompts[key]

        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful teacher's assistant that always responds using JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": formatted_template
                        }
                    ]
                }
            ],
            "response_format" : {"type": "json_object"},
            "max_tokens": 2500,
            "temperature": 0
        }

        if image_url_payload :
            payload['messages'][1]['content'].append(image_url_payload)

        try:
            # Convert the payload to JSON and encode as bytes for urllib
            json_data = json.dumps(payload).encode("utf-8")

            # Create the request
            request = urllib.request.Request(
                self.api_endpoint,
                data=json_data,
                headers=self.headers,
                method="POST"
            )

            # Make the request
            with urllib.request.urlopen(request) as response:
                if response.status == 200:
                    response_string = response.read().decode("utf-8")
                    response_json = json.loads(response_string)
                    response_content = response_json["choices"][0]["message"]["content"]

                    # Process and return the parsed JSON response
                    return self._process_chatgpt_response(response_content)
                else:
                    print(f"Error: {response.status}, {response.read().decode('utf-8')}")
                    return None
        except urllib.error.HTTPError as e:
            print(f"HTTPError: {e.code}, {e.read().decode('utf-8')}")
            return None
        except urllib.error.URLError as e:
            print(f"URLError: {e.reason}")
            return None
        except Exception as e:
            print(f"Error while calling ChatGPT: {e}")
            return None
