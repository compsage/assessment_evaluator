import os
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from image_handling import SourceImage
from assessment_grader import AssessmentGrader
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

def format_assessment_output(data: Dict[str, Any]) -> str:
    """
    Format the graded assessment data into a readable string output
    
    Args:
        data (Dict[str, Any]): The graded assessment data containing student info, questions, and scores
        
    Returns:
        str: Formatted string representation of the assessment results
    """
    # Build the header section
    header = f"""
Assessment Results
----------------
Student: {data.get('student_name')}
Date: {data.get('date')}
Assessment: {data.get('name')}
Subject: {data.get('subject')}
Section: {data.get('section')}
"""

    # Build the questions section
    questions_section = "\nQuestion Breakdown\n-----------------\n"
    for question_number, question_data in data.get('questions', {}).items():
        result = "✓" if question_data.get('correct') else "✗"
        points = question_data.get('value', 0)
        earned = points if question_data.get('correct') else (points/2 if question_data.get('partial_credit') else 0)
        
        questions_section += f"Q{question_number}. [{result}] {earned}/{points} points\n"
        questions_section += f"Comments: {question_data.get('comments', 'No comments provided')}\n"

    # Build the summary section
    summary = f"""
Overall Performance
------------------
Points Earned: {data.get('earned_points', 0)}/{data.get('total_points', 0)}
Final Grade: {data.get('grade', 0)}%

Performance Overview
-------------------
{data.get('overview', 'No overview provided')}
"""

    # Combine all sections
    return header + questions_section + summary

def execute_grading_pipeline(source_image_file: str, answer_key_file: str, asssessment_name: str, verbose_mode: bool = False, debug_mode: bool = False) -> Optional[Tuple[str, str, str]]:
    """
    Executes the grading pipeline.
    
    Args:
        source_image_file (str): The file path of the student quiz image
        answer_key_file (str): The file path of the answer key file
        asssessment_name (str): The name of the assessment in the answer key file; Note that the assessment name that can be extracted from the student quiz is not used to ensure consistency
        verbose_mode (bool): Whether to run in verbose mode
        debug_mode (bool): Whether to run in debug mode
    """
    
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
    if verbose_mode:
        print("\nGetting Student Quiz Image...")
    source_image = SourceImage(source_image_file)
    
    if verbose_mode:
        print("\nConverting Student Quiz Image to JSON...")
    image_json = gen_ai.request_for_image_json(source_image=source_image,
                                             payload=payload)
    # image_json = {'student_name': 'Jon Luther White', 'date': '2024-10-06', 'name': 'Quiz 1', 'subject': 'Intermediate Mathematics', 'section': '1.1–1.2', 'page': 1, 'questions': [{'text': 'In which number does the 6 have a greater value: 7,685 or 6,785?', 'student_answer': '6,785', 'generated_answer': '6,785', 'number': 1, 'correct_value': 'fully_correct', 'assessment': 'The student correctly identified the number with the greater value of 6.'}, {'text': 'In the number 243,107,569, which digit is in the ten thousands place?', 'student_answer': '0', 'generated_answer': '0', 'number': 2, 'correct_value': 'fully_correct', 'assessment': 'The student correctly identified the digit in the ten thousands place.'}, {'text': 'Round 4,482,186 to the tens place.', 'student_answer': '4,482,190', 'generated_answer': '4,482,190', 'number': 3, 'correct_value': 'fully_correct', 'assessment': 'The student correctly rounded the number to the tens place.'}, {'text': 'What is the answer to a subtraction problem called?', 'student_answer': 'difference', 'generated_answer': 'difference', 'number': 4, 'correct_value': 'fully_correct', 'assessment': 'The student correctly named the result of a subtraction problem.'}, {'text': 'What is the value of |-36|?', 'student_answer': '36', 'generated_answer': '36', 'number': 5, 'correct_value': 'fully_correct', 'assessment': 'The student correctly calculated the absolute value.'}, {'text': 'What number category includes whole numbers as well as their opposites?', 'student_answer': 'integers', 'generated_answer': 'integers', 'number': 6, 'correct_value': 'fully_correct', 'assessment': 'The student correctly identified the number category.'}, {'text': 'Compare each pair of numbers and write the correct symbol in the blank (>, <, or =). 7. 0.233 ___ 0.33', 'student_answer': '<', 'generated_answer': '<', 'number': 7, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the numbers.'}, {'text': '8. -2 ___ -11', 'student_answer': '>', 'generated_answer': '>', 'number': 8, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the numbers.'}, {'text': '9. |-7| ___ 10', 'student_answer': '<', 'generated_answer': '<', 'number': 9, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the absolute value.'}, {'text': '10. 25.19 ___ 25.2', 'student_answer': '<', 'generated_answer': '<', 'number': 10, 'correct_value': 'fully_correct', 'assessment': 'The student correctly compared the numbers.'}, {'text': 'Find the answers. 11. 7,365 + 12,719 + 2,574', 'student_answer': '22,658', 'generated_answer': '22,658', 'number': 11, 'correct_value': 'fully_correct', 'assessment': 'The student correctly calculated the sum.'}, {'text': '12. 14.56 - 3.054', 'student_answer': '11.57', 'generated_answer': '11.506', 'number': 12, 'correct_value': 'partially_correct', 'assessment': 'The student made a small error in subtraction.'}, {'text': '13. 47.8 × 1.2', 'student_answer': '57.36', 'generated_answer': '57.36', 'number': 13, 'correct_value': 'fully_correct', 'assessment': 'The student correctly calculated the product.'}, {'text': '14. 0.6 ÷ 1.944', 'student_answer': '0.3', 'generated_answer': '0.3086', 'number': 14, 'correct_value': 'partially_correct', 'assessment': 'The student made a small error in division.'}]}
    # print(f"\nStudent Quiz Answer: {image_json}")
    
    # Evaluate and grade the student's quiz against the answer key
    assessment_grader = AssessmentGrader(gen_ai=gen_ai)
    if verbose_mode:
        print("\nGrading Quiz...")
    try:
        graded_quiz = assessment_grader.grade(answer_key_file=answer_key_file, 
                                                 assessment_name=asssessment_name, # The name of the assessment retrieved from the student quiz
                                                 student_answers=image_json)
    except Exception as e:
        if verbose_mode:
            print(f"Error grading quiz: {e}")
        if debug_mode:
            return image_json, None, None
        else:
            return None
    
    # Format the graded quiz for output
    if verbose_mode:
        print("\nFormatting Quiz...")
    formatted_quiz = format_assessment_output(graded_quiz)
    if verbose_mode:
        print(f"\n{formatted_quiz}")

    if debug_mode:
        return image_json, graded_quiz, formatted_quiz
    else:
        return None

if __name__ == "__main__":
    execute_grading_pipeline(source_image_file="data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg",
                             answer_key_file="data/transformed_answer_keys.json",
                             asssessment_name="quiz 1",
                             verbose_mode=True)
