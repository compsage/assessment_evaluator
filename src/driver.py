import json
import os
from dotenv import load_dotenv
from pathlib import Path

from image_handling import SourceImage
from assessment_handler import AssessmentHandler, Evaluator
from gen_ai import GenAI

def get_file_paths(directory):
    """
    Retrieves all file paths from a specific directory.

    :param directory: Path to the directory.
    :return: List of file paths.
    """
    file_paths = []
    if not os.path.exists(directory):
        print(f"Directory '{directory}' does not exist.")
        return file_paths

    target_extensions = (".jpeg", ".png", ".jpg")

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if file_path.endswith(target_extensions):
                file_paths.append(file_path)

    return file_paths

# def generate_answer_keys(directory_path) :
#     image_processor = Evaluator("../prompts", openai_api_key=openai_api_key)
#     answer_key_image_paths = get_file_paths(directory_path)

#     #You only need to run this once because onece the answers are extracted you can just use the json to check
#     answer_key_images = []
#     for answer_key_image_path in answer_key_image_paths :
#         answer_key_images.append(SourceImage(answer_key_image_path)) 

#     answers = image_processor.call_genai_multi_threaded(answer_key_images, "get_questions_answers_from_key", )
    
#     for key in answers :
#         # Original file path
#         file_path = Path(key)
#         # Replace extension with .json
#         output_file = file_path.with_suffix(".json")
#         with open(output_file, "w", encoding="utf-8") as json_file:
#             json.dump(answers[key], json_file, indent=4, ensure_ascii=False)
     
# NOTE: OLD AND WILL NEED REWORK; HERE FOR REFERENCE       
# def call_genai_multi_threaded(self, images, key, max_workers=5):
#     """
#     Processes a list of SourceImage objects concurrently and extracts data from them.

#     :param images: List of SourceImage objects to process.
#     :param key: The key to fetch the prompt for processing.
#     :param max_workers: Maximum number of concurrent workers (default is 5).
#     :return: A dictionary where keys are image indices and values are the results or errors.
#     """
#     results = {}

#     with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
#         future_to_index = {
#             executor.submit(self.call_genai, image, key, **{}): image.get_source() for image in images
#         }

#         for future in concurrent.futures.as_completed(future_to_index):
#             source = future_to_index[future]
#             try:
#                 result = future.result()
#                 results[source] = result
#             except Exception as e:
#                 print(e)
#                 print(f"error -> {source}")

#     return results

if __name__ == "__main__":
    '''#Get the answer key images to check the students answers.  No need to call this everytime
    #generate_answer_keys("../data/all_answer_key_images")

    #This is the "Master Key" of answers
    file_path = "./data/answer_keys.json"
    with open(file_path, "r", encoding="utf-8") as json_file:
        answer_keys = json.load(json_file)

    #Load each answer key into a dictionary for lookup
    answers = {}
    for answer_key in answer_keys:
        if answer_key:
            answers[answer_key["name"].lower()] = answer_key

    #Get the image of the student quiz
    student_quiz_image = SourceImage("./data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg")

    image_processor = Evaluator("./prompts")
    #Call ChatGPT with the image to get the students answers in JSON format
    student_answers = image_processor.call_genai(student_quiz_image, "get_answers_from_student_quiz")
    pprint.pprint(student_answers)

    #Now that we have the Students answers and the Keys Loaded lets grade it
    assessment_evaluator = AssessmentEvaluator("./prompts")

    #Perform the initial check of the student's quiz against the answer key
    checked_student_answers = assessment_evaluator.evaluate(answers["quiz 1"], student_answers)
    
    #No2 that it's been checked let's grade the exam
    graded_assessment = assessment_evaluator.grade(checked_student_answers)
    
    #Now output the text summary
    text_summary = assessment_evaluator.format(graded_assessment)
    print(text_summary)'''



        
        
    # Retrieve the prompt used to get the questions and answers from a student quiz
    with open("prompts/get_answers_from_student_quiz.txt", "r") as file:
        image_prompt = file.read()
            
    gen_ai = GenAI()
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

    # Get the image of the student quiz
    print("\nGetting Student Quiz Image...")
    source_image = SourceImage("data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg")
    
    print("\nConverting Student Quiz Image to JSON...")
    # response = gen_ai.request_for_image_json(source_image=source_image,
    #                                          payload=payload)
    response = {'student_name': 'Jon Luther White', 'date': '2024-10-06', 'name': 'Quiz 1', 'subject': 'Intermediate Mathematics', 'section': '1.1–1.2', 'page': 1, 'questions': [{'text': 'In which number does the 6 have a greater value: 7,685 or 6,785?', 'student_answer': '6,785', 'generated_answer': '6,785', 'number': 1, 'correct_value': 'fully_correct', 'assessment': 'The student correctly identified the number with the greater value of 6.'}, {'text': 'In the number 243,107,569, which digit is in the ten thousands place?', 'student_answer': '0', 'generated_answer': '0', 'number': 2, 'correct_value': 'fully_correct', 'assessment': 'The student correctly identified the digit in the ten thousands place.'}, {'text': 'Round 4,482,186 to the tens place.', 'student_answer': '4,482,190', 'generated_answer': '4,482,190', 'number': 3, 'correct_value': 'fully_correct', 'assessment': 'The student correctly rounded the number to the tens place.'}, {'text': 'What is the answer to a subtraction problem called?', 'student_answer': 'difference', 'generated_answer': 'difference', 'number': 4, 'correct_value': 'fully_correct', 'assessment': 'The student correctly named the result of a subtraction problem.'}, {'text': 'What is the value of |-36|?', 'student_answer': '36', 'generated_answer': '36', 'number': 5, 'correct_value': 'fully_correct', 'assessment': 'The student correctly calculated the absolute value.'}, {'text': 'What number category includes whole numbers as well as their opposites?', 'student_answer': 'integers', 'generated_answer': 'integers', 'number': 6, 'correct_value': 'fully_correct', 'assessment': 'The student correctly identified the number category.'}, {'text': 'Compare each pair of numbers and write the correct symbol in the blank (>, <, or =). 7. 0.233 ___ 0.33', 'student_answer': '<', 'generated_answer': '<', 'number': 7, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the numbers.'}, {'text': '8. -2 ___ -11', 'student_answer': '>', 'generated_answer': '>', 'number': 8, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the numbers.'}, {'text': '9. |-7| ___ 10', 'student_answer': '<', 'generated_answer': '<', 'number': 9, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the absolute value.'}, {'text': '10. 25.19 ___ 25.2', 'student_answer': '<', 'generated_answer': '<', 'number': 10, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the numbers.'}, {'text': 'Find the answers. 11. 7,365 + 12,719 + 2,574', 'student_answer': '22,658', 'generated_answer': '22,658', 'number': 11, 'correct_value': 'fully_correct', 'assessment': 'The student correctly calculated the sum.'}, {'text': '12. 14.56 - 3.054', 'student_answer': '11.57', 'generated_answer': '11.506', 'number': 12, 'correct_value': 'partially_correct', 'assessment': 'The student made a small error in subtraction.'}, {'text': '13. 47.8 × 1.2', 'student_answer': '57.36', 'generated_answer': '57.36', 'number': 13, 'correct_value': 'fully_correct', 'assessment': 'The student correctly calculated the product.'}, {'text': '14. 0.6 ÷ 1.944', 'student_answer': '0.3', 'generated_answer': '0.3086', 'number': 14, 'correct_value': 'partially_correct', 'assessment': 'The student made a small error in division.'}]}
    print(f"\nStudent Quiz Answer: {response}")
    
    # Evaluate the student's quiz against the answer key
    assessment_evaluator = AssessmentHandler(gen_ai=gen_ai)
    print("\nEvaluating Quiz...")
    evaluated_quiz = assessment_evaluator.evaluate("data/transformed_answer_keys.json", "quiz 1", response) # NOTE: It's only returning only the correct answers like this temporarily
    print(f"\nEvaluated Quiz: {evaluated_quiz}")
    
    # Grade the student's quiz
    # print("\nGrading Quiz...")
    # graded_quiz = assessment_evaluator.grade(evaluated_quiz)
