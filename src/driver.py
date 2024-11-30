import json
import os
import pprint
from pathlib import Path

from SourceImage import SourceImage
from Processors import Processor
from Evaluator import AssessmentEvaluator

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

    target_extensions = ('.jpeg', '.png', '.jpg')

    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if file_path.endswith(target_extensions):
                file_paths.append(file_path)

    return file_paths

def generate_answer_keys(directory_path) :
    answer_key_image_paths = get_file_paths(directory_path)

    #You only need to run this once because onece the answers are extracted you can just use the json to check
    answer_key_images = []
    for answer_key_image_path in answer_key_image_paths :
        answer_key_images.append(SourceImage(answer_key_image_path))

    answers = image_processor.call_genai_multi_threaded(answer_key_images, "get_questions_answers_from_key", )
    
    for key in answers :
        # Original file path
        file_path = Path(key)
        # Replace extension with .json
        output_file = file_path.with_suffix(".json")
        with open(output_file, "w", encoding="utf-8") as json_file:
            json.dump(answers[key], json_file, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    #Get the answer key images to check the students answers.  No need to call this everytime
    #generate_answer_keys("../data/answer_key_images")
    
    #This is the 'Master Key' of answers
    file_path = '../data/answer_keys.json'
    with open(file_path, "r", encoding="utf-8") as json_file:
        answer_keys = json.load(json_file)

    #Load each answer key into a dictionary for lookup
    answers = {}
    for answer_key in answer_keys :
        if answer_key:
            answers[answer_key['name'].lower()] = answer_key

    #Get the image of the student quiz
    student_quiz_image = SourceImage("../data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg")

    image_processor = Processor()
    #Call ChatGPT with the image to get the students answers in JSON format
    student_answers = image_processor.call_genai(student_quiz_image, "get_answers_from_student_quiz")
    pprint.pprint(student_answers)

    #Now that we have the Students answers and the Keys Loaded lets grade it
    assessment_evaluator = AssessmentEvaluator()

    #Perform the initial check of the student's quiz against the answer key
    checked_student_answers = assessment_evaluator.check(answers['quiz 1'], student_answers)
    
    #No2 that it's been checked let's grade the exam
    graded_assessment = assessment_evaluator.grade(checked_student_answers)
    
    #Now output the text summary
    text_summary = assessment_evaluator.format(graded_assessment)
    print(text_summary)