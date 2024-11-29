
from Processors import Processor
import os
import pprint
import json
import math
import urllib.request
import urllib.error
import concurrent.futures

class AssessmentEvaluator(Processor) :
    def process(self):
        """
        Processes a SourceImage object. Placeholder for custom operations.

        :param source_image: The SourceImage object to process.
        :param kwargs: Additional parameters for processing (optional).
        :return: None
        """

    def extract_data_from_images(self, images, key, max_workers=5):
        """
        Processes a list of SourceImage objects concurrently and extracts data from them.

        :param images: List of SourceImage objects to process.
        :param key: The key to fetch the prompt for processing.
        :param max_workers: Maximum number of concurrent workers (default is 5).
        :return: A dictionary where keys are image indices and values are the results or errors.
        """
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_index = {
                executor.submit(self.extract_data_from_image, image, key): index for index, image in enumerate(images)
            }

            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({f"error_{index}": str(e)})

        return results

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

            analysis_output = self.call_genai('evaluate_answer', **values)
            output.append({**answer, 'analysis' : analysis_output})

        return output
    
    def grade(self, answers, student_quiz) :
        correct_answers = []
        partially_correct_answers = []
        incorrect_answers = []
        overall_points = 0
        total_points = 0
        for answer in answers:
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
                        total_points += math.ceil(answer['value']/2)
                        partially_correct_answers.append((answer['number'], math.floor(answer['value']/2)))
                    else :
                        incorrect_answers.append((answer['number'], answer['value']))
                else :
                    incorrect_answers.append((answer['number'], answer['value']))

        explanations = ''
        for aq in answers :
            if 'analysis' in aq and aq['analysis'] :
                explanations += aq['analysis']['explanation']
                explanations += '\n'

        kwargs = {'explanations' : explanations}
        performance = self.call_genai('summarize_performance', **kwargs)

        qd = {str(k): str(v) for k, v in student_quiz.items()}
        del qd['questions']

        summary = {
            **qd,
            'correct' : correct_answers,
            'incorrect' : incorrect_answers,
            'partially_correct' : partially_correct_answers,
            'grade' : (total_points/overall_points) * 100,
            'total_points' : total_points,
            'overall_points' : overall_points,
            'assessment' : answers,
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
        incorrect = data.get('incorrect', [])

        # Extract question numbers as comma-separated strings
        correct_numbers = ", ".join(str(question) for question, _ in correct)
        partial_numbers = ", ".join(str(question) for question, _ in partial)
        incorrect_numbers = ", ".join(str(question) for question, _ in incorrect)

        # Total points for each category
        correct_points = sum(points for _, points in correct)
        partial_points = sum(points for _, points in partial)
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
            f"Partially Correct Answers: {partial_numbers} ({partial_points} points)\n"
            f"Incorrect Answers: {incorrect_numbers} ({incorrect_points} points)\n"
            f"Total Points: {total_points} points\n\n"
            f"{performance_overview}\n"
        )

        return formatted_output

    def call_genai(self, key, **kwargs) :

        formatted_template = self.prompts[key].format(**kwargs)

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
            "max_tokens": 2500,
            "temperature": 0
        }

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