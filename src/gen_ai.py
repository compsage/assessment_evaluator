from typing import Any, Dict
import json
import os
from dotenv import load_dotenv
import urllib.request
import urllib.error
from image_handling import SourceImage

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

class GenAI:
    # NOTE: This will be the default endpoint and headers until others and/or AI providers are added
    endpoint = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }
    
    def request(self, payload: Dict[str, str]) -> Dict[str, Any]:
        """
        Makes a request to the Gen AI endpoint and returns the response.

        Args:
            payload (Dict[str, str]): The request payload/body as a dictionary

        Returns:
            Dict[str, Any]: The response from the API, or None if there was an error
        """
        
        try:
            # Convert the payload to JSON and encode as bytes for urllib
            json_data = json.dumps(payload).encode("utf-8")

            # Create the request
            request = urllib.request.Request(
                self.endpoint,
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
                
                    if not response_content:
                        print(f"Response from AI Empty: {response_content}")
                        return None
                    else:
                        return response_content
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
        
    def request_json(self, payload: Dict[str, str]) -> Dict[str, Any]:
        """
        Makes a request to the Gen AI endpoint and returns the parsed JSON response.

        Args:
            payload (Dict[str, str]): The request payload/body as a dictionary

        Returns:
            Dict[str, Any]: The parsed JSON response from the API, or None if there was an error
        """
        
        response_content = self.request(payload=payload)
        if not response_content:
            return None
        
        # Process and return the parsed JSON response
        try:
            # Remove the markdown code block
            if response_content.startswith("```json"):
                response_content = response_content[len("```json"):].strip()
            if response_content.endswith("```"):
                response_content = response_content[:-len("```")].strip()
            return json.loads(response_content)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}\n raw_response: {response_content}")
            return None
        
    def _add_image_to_payload(self, source_image: SourceImage, payload: Dict[str, str]) -> None:
        """
        Adds the image to the payload

        Args:
            source_image (SourceImage): The image to add to the payload
            payload (Dict[str, str]): The payload to add the image to
        """
        
        image_url = f"data:image/jpeg;base64,{source_image.get_base64()}"
        image_url_payload = {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            }
        payload["messages"][1]["content"].append(image_url_payload)

    def request_for_image_text(self, source_image: SourceImage, payload: Dict[str, str]) -> Dict[str, Any]:
        """
        Makes a request to the Gen AI endpoint and returns the text response.

        Args:
            source_image (SourceImage): The image to add to the payload
            payload (Dict[str, str]): The payload to add the image to

        Returns:
            Dict[str, Any]: The response from the API, or None if there was an error
        """
        
        print(f"Sending {source_image.get_source()} to: {self.endpoint}")
        self._add_image_to_payload(source_image=source_image, payload=payload)
        return self.request(payload=payload)
    
    def request_for_image_json(self, source_image: SourceImage, payload: Dict[str, str]) -> Dict[str, Any]:
        """
        Makes a request to the Gen AI endpoint and returns the JSON response.

        Args:
            source_image (SourceImage): The image to add to the payload
            payload (Dict[str, str]): The payload to add the image to

        Returns:
            Dict[str, Any]: The response from the API, or None if there was an error
        """
        
        print(f"Sending {source_image.get_source()} to: {self.endpoint}")
        self._add_image_to_payload(source_image=source_image, payload=payload)
        return self.request_json(payload=payload)
        
if __name__ == "__main__":
    load_dotenv()

    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Read the contents of the file
    with open("prompts/get_questions_answers_from_key.txt", "r") as file:
        image_prompt = file.read()
    
    gen_ai = GenAI()
    endpoint = "https://api.openai.com/v1/chat/completions"
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
                            "text": image_prompt
                        }
                    ]
                }
            ],
            "response_format" : {"type": "json_object"},
            "max_tokens": 2500,
            "temperature": 0
        }

    source_image = SourceImage("data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg")
    response = gen_ai.request_for_image_json(source_image=source_image,
                                             payload=payload)
    print(response)