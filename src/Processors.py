
import math
import os
import json
import urllib.request
import urllib.error
import concurrent.futures
from abc import ABC, abstractmethod
from image_handling import SourceImage

class Processor(ABC):
    """
    Abstract base class for processing objects and managing prompts.
    """
    api_endpoint = "https://api.openai.com/v1/chat/completions"
    

    def __init__(self, prompts_directory="./prompts", openai_api_key=None):
        """
        Initializes the Processor and loads prompt files from the specified directory.

        :param prompts_directory: Path to the directory containing .txt prompt files.
        """
        self.prompts = self._load_prompts(prompts_directory)

        self.headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

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

class AssessmentProcessor(Processor) :
    def process(self):
        print("Process Method...")

    def check(self, answer_key, student_assessment) :
        ql = []
        output = []
        for correct_answer in answer_key['questions'] :
            for student_answer in student_assessment['questions'] :
                if correct_answer['number'] == student_answer['number'] :
                    if student_answer['student_answer'] in correct_answer['answer'] :
                        ql.append({**correct_answer, **student_answer, 'answer_match' : True})
                        output.append({**correct_answer, **student_answer, 'answer_match' : True})
                    else :
                        ql.append({**correct_answer, **student_answer, 'answer_match' : False})
    

        for answer in ql :
            if answer['answer_match'] :
                continue
            
            values = {  'key_text': answer['text'], 
                        'key_answer' : answer['answer'], 
                        'student_answer' : answer['student_answer']
                    }

            analysis_output = self.call_genai(None, 'evaluate_answer', **values)
            output.append({**answer, 'analysis' : analysis_output})

        student_assessment['checked_answers'] = output
        return student_assessment
    
    def grade(self, student_assessment) :
        correct_answers = []
        partially_correct_answers = []
        partially_correct_diffs = []
        incorrect_answers = []
        overall_points = 0
        total_points = 0
        for answer in student_assessment['checked_answers']:
            overall_points += answer['value']
            if answer['answer_match'] :
                total_points += answer['value']
                correct_answers.append((answer['number'], answer['value']))
            else :
                #pprint.pprint(answer)
                if 'analysis' in answer and answer['analysis']:
                    if 'correct' in answer['analysis'] and answer['analysis']['correct'] :
                        total_points += answer['value']
                        correct_answers.append((answer['number'], answer['value']))
                    elif 'partial_credit' in answer['analysis'] and answer['analysis']['partial_credit'] :
                        add_value = math.ceil(answer['value']/2)
                        diff_value = (answer['value'] - add_value)
                        total_points += add_value
                        partially_correct_answers.append((answer['number'], math.floor(answer['value']/2)))
                        partially_correct_diffs.append((answer['number'], diff_value))
                    else :
                        incorrect_answers.append((answer['number'], answer['value']))
                else :
                    incorrect_answers.append((answer['number'], answer['value']))

        explanations = ''
        for aq in student_assessment['checked_answers'] :
            if 'analysis' in aq and aq['analysis'] :
                explanations += aq['analysis']['explanation']
                explanations += '\n'

        kwargs = {'explanations' : explanations}
        performance = self.call_genai(None, 'summarize_performance', **kwargs)

        summary = {
            'student_name' : student_assessment['student_name'],
            'date' : student_assessment['date'],
            'name' : student_assessment['name'],
            'subject' : student_assessment['subject'],
            'section' : student_assessment['section'],
            'correct' : correct_answers,
            'incorrect' : incorrect_answers,
            'partially_correct' : partially_correct_answers,
            'partially_correct_diffs' : partially_correct_diffs,
            'grade' : (total_points/overall_points) * 100,
            'total_points' : total_points,
            'overall_points' : overall_points,
            'assessment' : student_assessment['checked_answers'],
            'performance_overview' : performance['overview']   
            }

        text_summary = self.format(summary)
        summary['text_summary'] = text_summary

        return summary

    def format(self, data):
        # Extract relevant fields from the JSON
        student_name = data.get('student_name', 'Unknown')
        assessment_name = data.get('name', 'Unknown')
        assessment_subject = data.get('subject', 'Unknown')
        date = data.get('date', 'Unknown')

        # Prepare lists for correct, partially correct, and incorrect answers
        correct = data.get('correct', [])
        partial = data.get('partially_correct', [])
        partial_diff =  data.get('partially_correct_diffs', [])
        incorrect = data.get('incorrect', [])

        # Extract question numbers as comma-separated strings
        correct_numbers = ", ".join(str(question) for question, _ in correct)
        partial_numbers = ", ".join(str(question) for question, _ in partial)
        incorrect_numbers = ", ".join(str(question) for question, _ in incorrect)

        # Total points for each category
        correct_points = sum(points for _, points in correct)
        partial_points = sum(points for _, points in partial)
        partial_diff = sum(points for _, points in partial_diff)
        incorrect_points = -sum(points for _, points in incorrect)  # Negative for incorrect

        total_points = correct_points + partial_points
        # Overall points and performance overview
        overall_points = data.get('overall_points', 0)
        total_possible_points = correct_points + partial_points - incorrect_points
        performance_percentage = (overall_points / total_possible_points) * 100 if total_possible_points else 0

        # Performance overview
        performance_overview = data.get('performance_overview')

        # Format the output string
        formatted_output = (
            f"Student Name: {student_name}\n"
            f"Date: {date}\n"
            f"Assessment Subject: {assessment_subject}\n"
            f"Assessment Name: {assessment_name}\n\n"
            
            f"Correct Answers: {correct_numbers} ({correct_points} points)\n"
            f"Partially Correct Answers: {partial_numbers} ({partial_points} points, {-partial_diff} points)\n"
            f"Incorrect Answers: {incorrect_numbers} ({incorrect_points} points)\n"
            f"Points Subtracted: {(incorrect_points + -partial_diff)} points\n"
            f"Total Points: {total_points} points\n\n"
            f"{performance_overview}\n"
        )

        return formatted_output