import json
import os
import pprint
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from SourceImage import SourceImage
from Processors import Processor
from Evaluator import AssessmentEvaluator

openai_api_key = os.getenv("OPENAI_API_KEY")

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

def annotate_grade(image_path, graded_data):
    annotated_image = Image.open(image_path)
    draw = ImageDraw.Draw(annotated_image)

    # Define font for annotations and grade
    font_path = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"  # Adjust for macOS
    font = ImageFont.truetype(font_path, size=40)
    grade_font = ImageFont.truetype(font_path, size=100)  # Larger font for overall grade

    # Add overall grade to the top-right corner
    overall_grade = graded_data.get("grade", 0)
    if overall_grade > 80:
        grade_color = "darkgreen"
    elif 65 <= overall_grade <= 80:
        grade_color = "yellow"
    else:
        grade_color = "red"

    # Calculate position for the grade
    image_width, image_height = annotated_image.size
    text_x = image_width - 150  # Adjust closer to the right edge
    text_y = 50  # Top padding for the grade
    draw.text((text_x, text_y), f"{overall_grade}", fill=grade_color, font=grade_font)

    # Write list of numbers with annotations directly under the grade
    start_y = text_y + 120  # Move the list closer to the grade
    line_height = 50  # Spacing between lines

    # Add annotations for each number
    annotations = {}

    # Add correct answers
    for correct in graded_data["correct"]:
        number = f"{correct[0]}"
        annotations[number] = ("c", "darkgreen")

    # Add incorrect answers
    for incorrect in graded_data["incorrect"]:
        number = f"{incorrect[0]}"
        diff = next((item[1] for item in graded_data["incorrect"] if item[0] == int(number)), 0)
        annotations[number] = (f"x -{diff}", "red")

    # Add partially correct answers
    for partial in graded_data["partially_correct"]:
        number = f"{partial[0]}"
        diff = next((diff[1] for diff in graded_data["partially_correct_diffs"] if diff[0] == partial[0]), 0)
        annotations[number] = (f"x -{diff}", "yellow")

    # Write annotations to the image in order
    for idx, number in enumerate(sorted(annotations.keys(), key=lambda x: int(x))):
        annotation, color = annotations[number]
        text = f"{number}: {annotation}"
        draw.text((text_x, start_y + idx * line_height), text, fill=color, font=font)

    # Save the annotated image with a modified name
    base, ext = os.path.splitext(image_path)
    output_path = f"{base}_annotations.png"
    annotated_image.save(output_path)
    print(f"Annotated worksheet saved as {output_path}!")

def generate_answer_keys(directory_path) :
    image_processor = Processor("../prompts", openai_api_key=openai_api_key)
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
    #generate_answer_keys("../data/all_answer_key_images")

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

    image_processor = Processor(openai_api_key=openai_api_key)
    #Call ChatGPT with the image to get the students answers in JSON format
    student_answers = image_processor.call_genai(student_quiz_image, "get_answers_from_student_quiz")
    pprint.pprint(student_answers)

    #Now that we have the Students answers and the Keys Loaded lets grade it
    assessment_evaluator = AssessmentEvaluator(openai_api_key=openai_api_key)

    #Perform the initial check of the student's quiz against the answer key
    checked_student_answers = assessment_evaluator.check(answers['quiz 1'], student_answers)
    
    #No2 that it's been checked let's grade the exam
    graded_assessment = assessment_evaluator.grade(checked_student_answers)
    
    annotate_grade(student_quiz_image.get_source(), graded_assessment)
    
    #Now output the text summary
    text_summary = assessment_evaluator.format(graded_assessment)
    print(text_summary)