import json
import os
import pprint
from source_image import SourceImage
from Processors import Processor
from Evaluator import AssessmentEvaluator
from dotenv import load_dotenv

load_dotenv()

openai_api_key = os.getenv("OPENAI_API_KEY")

if __name__ == "__main__":
    # Get the answer key images to check the students answers.  No need to call this everytime
    # generate_answer_keys("../data/all_answer_key_images")

    # This is the 'Master Key' of answers
    file_path = '../data/answer_keys.json'
    with open(file_path, "r", encoding="utf-8") as json_file:
        answer_keys = json.load(json_file)

    # Load each answer key into a dictionary for lookup
    answers = {}
    for answer_key in answer_keys:
        if answer_key:
            answers[answer_key['name'].lower()] = answer_key

    # Get the image of the student quiz
    student_quiz_image = SourceImage("../data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg")

    image_processor = Processor("../prompts", openai_api_key=openai_api_key)
    
    # Call ChatGPT with the image to get the students answers in JSON format
    student_answers = image_processor.call_genai(student_quiz_image, "get_answers_from_student_quiz")
    pprint.pprint(student_answers)

    # Now that we have the Students answers and the Keys Loaded lets grade it
    assessment_evaluator = AssessmentEvaluator("../prompts", openai_api_key=openai_api_key)

    # Perform the initial check of the student's quiz against the answer key
    checked_student_answers = assessment_evaluator.check(answers['quiz 1'], student_answers)
    
    # No2 that it's been checked let's grade the exam
    graded_assessment = assessment_evaluator.grade(checked_student_answers)
    
    # Now output the text summary
    text_summary = assessment_evaluator.format(graded_assessment)
    print(text_summary)