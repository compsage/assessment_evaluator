from PIL import Image, ImageDraw, ImageFont
import pytesseract
import cv2
import json
import os

# Load the image
image_path = "../data/student_assessment_images/media_0_MEc26c0f087a170ee977e9126f27c2de1a_1732593820049.jpeg"
image = cv2.imread(image_path)

# Convert image to grayscale (improves OCR accuracy)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Perform OCR with bounding box extraction
data = pytesseract.image_to_data(gray, output_type=pytesseract.Output.DICT)

# Initialize Pillow image for annotation
annotated_image = Image.open(image_path)
draw = ImageDraw.Draw(annotated_image)

# Define font for annotations (bold and large)
font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"  # Adjust for macOS
font = ImageFont.truetype(font_path, size=40)
grade_font = ImageFont.truetype(font_path, size=100)  # Larger font for overall grade

# Load the graded JSON file
graded_json_path = "graded.json"
with open(graded_json_path, "r") as json_file:
    graded_data = json.load(json_file)

# Build the annotations dictionary from graded data
annotations = {}

# Add correct answers
for correct in graded_data["correct"]:
    number = f"{correct[0]}."  # Correct syntax
    annotations[number] = "c"

# Add incorrect answers
for incorrect in graded_data["incorrect"]:
    number = f"{incorrect[0]}."  # Correct syntax
    annotations[number] = "x"

# Add partially correct answers
for partial in graded_data["partially_correct"]:
    number = f"{partial[0]}."  # Correct syntax
    diff = next((diff[1] for diff in graded_data["partially_correct_diffs"] if diff[0] == partial[0]), 0)
    annotations[number] = f"x -{diff}"

# Loop through OCR results and find numbers matching the pattern
for i in range(len(data['text'])):
    text = data['text'][i].strip()

    # Check if text matches the number pattern (e.g., '1.', '2.', etc.)
    if text in annotations:
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        print(f"Found number '{text}' at ({x}, {y}, {w}, {h})")

        # Get the annotation for the number
        annotation = annotations[text]

        # Determine the color based on annotation
        color = "darkgreen" if annotation.startswith("c") else "red"

        # Write the annotation to the left of the number
        draw.text((x - 60, y - 10), annotation, fill=color, font=font)

# Add overall grade to the right of the image
overall_grade = graded_data.get("grade", 0)
if overall_grade > 80:
    grade_color = "darkgreen"
elif 65 <= overall_grade <= 80:
    grade_color = "yellow"
else:
    grade_color = "red"

# Calculate position for the grade
image_width, image_height = annotated_image.size
text_x = image_width - 300  # Adjust as needed for padding
text_y = 50  # Top padding for the grade

draw.text((text_x, text_y), f"{overall_grade}", fill=grade_color, font=grade_font)

# Save the annotated image with a modified name
base, ext = os.path.splitext(image_path)
output_path = f"{base}_annotations.png"
annotated_image.save(output_path)
print(f"Annotated worksheet saved as {output_path}!")
