import boto3
import json
import base64
import re
from datetime import datetime
import time
from urllib.parse import parse_qs
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

from image_handling import SourceImage
from Processors import Processor
from Evaluator import AssessmentEvaluator

def detect_double_exclamation_commands(text):
    """
    Detects and extracts commands prefixed with !! from the input text.
    
    Args:
        text (str): The input string containing commands.
    
    Returns:
        list: A list of detected commands (excluding arguments).
    """
    # Regex to match the !! prefix followed by a command
    command_pattern = r"!!(\w+)"
    commands = re.findall(command_pattern, text)
    return commands

def validate_twilio_request(event):

    # Extract data from the event
    twilio_signature = event["headers"].get("x-twilio-signature")
    print(twilio_signature)
    request_url = "https://4yaapzlnl5d7lax72bxgn6bemq0aqjbb.lambda-url.us-east-1.on.aws/"
    
    query_params = event.get("queryStringParameters", {})

    # Parse the body as form parameters (for application/x-www-form-urlencoded)
    event_body = event.get('body', '{}')

    if event.get('isBase64Encoded', False):
        body_params = parse_qs(base64.b64decode(event_body).decode('utf-8'))
    else:
        body_params = parse_qs(event_body)
    
    if twilio_signature and body_params['MessagingServiceSid'][0] == 'MG20131941589f8a718941c56a9111b6fe' and body_params['From'][0] == '+12025283496' :
        return True
    else :
        return False

# Main Lambda handler
def handler(event, context):
    # AWS Configurations
    ssm_client = boto3.client('ssm')

    # Utilities for Date and Time
    current_date = datetime.utcnow().strftime('%Y/%m/%d')
    current_time_millis = int(time.time() * 1000)
    
    account_sid = get_parameter(ssm_client, 'twillio_account_sid')
    auth_token = get_parameter(ssm_client, 'twillio_auth_token')
    bucket_name = get_parameter(ssm_client, 'from_twillio_bucket_name')
    openai_api_key = get_parameter(ssm_client, 'openai_api_key')

    if not validate_twilio_request(event) :
        print("Not Validated")
        return 
    else :
        print("Valid Request")

    try:
        # Parse and decode the event body
        event_body = event.get('body', {})
        if event.get('isBase64Encoded', False):
            event_body = parse_qs(base64.b64decode(event_body).decode('utf-8'))
        else:
            event_body = parse_qs(event_body)

        # Convert all values to strings
        event_body = {key: value[0] for key, value in event_body.items()}

        num_media = int(event_body.get('NumMedia', 0))
        if num_media == 0:
            print("No media URLs in the payload.")
            return {}

        sourceImages = []
        for i in range(num_media):
            media_url = event_body.get(f'MediaUrl{i}')
            media_type = event_body.get(f'MediaContentType{i}', 'unknown')
            tail = media_url.split('/')[-1]
            file_type = media_type.split('/')[-1]

            sourceImage = SourceImage(media_url, auth=(account_sid, auth_token), additional_metadata=event_body)
            bucket_path = f"s3://{bucket_name}/{current_date}/{current_time_millis}"
            filename = f"media_{i}_{tail}_{current_time_millis}.{file_type}"
            sourceImage.write(bucket_path, filename)
            sourceImages.append(sourceImage)

            if not media_url:
                continue

    except Exception as e:
        print(f"Error in Lambda handler: {e}")
        return {'statusCode': 500, 'body': 'Error processing media'}

    file_path = './data/answer_keys.json'
    with open(file_path, "r", encoding="utf-8") as json_file:
        answers = json.load(json_file)

    all_student_answers_dict = {}
    #Get the image of the student quiz
    #student_quiz_image = SourceImage("./data/quiz1_sample.jpeg")
    for student_assessment_image in sourceImages :
        image_processor = Processor(prompts_directory="./prompts", openai_api_key=openai_api_key)
        #Call ChatGPT with the image to get the students answers in JSON format
        student_answers = image_processor.call_genai(student_assessment_image, "get_answers_from_student_quiz")

        key = student_answers['name'].lower() + student_answers['student_name'].lower()
        if key not in all_student_answers_dict :
            all_student_answers_dict[key] = student_answers
        else :
            questions = student_answers.get("questions", [])
            all_student_answers_dict[key]['questions'].extend(questions)

    #Now that we have the Students answers and the Keys Loaded lets grade it
    assessment_evaluator = AssessmentEvaluator(prompts_directory="./prompts", openai_api_key=openai_api_key)

    #Need to combine test pages 
    for key in all_student_answers_dict :
        student_answers = all_student_answers_dict[key]
        
        #Perform the initial check of the student's quiz against the answer key
        checked_student_answers = assessment_evaluator.check(answers[student_answers['name'].lower()], student_answers)
    
        #No2 that it's been checked let's grade the exam
        graded_assessment = assessment_evaluator.grade(checked_student_answers)
    
        #Now output the text summary
        text_summary = assessment_evaluator.format(graded_assessment)
        #print(text_summary)

        subject = graded_assessment['name'] + " | " + graded_assessment['student_name'] + " | Grade: " + str(graded_assessment['grade']) 

        send_email('None', subject, text_summary)

    return {'status_code' : 201, 'body' : text_summary}

# Get Twilio credentials from AWS Systems Manager Parameter Store
def get_parameter(ssm_client, name):
    try:
        response = ssm_client.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Failed to retrieve parameter {name}: {e}")
        return None

def send_email(fn, subject, body):
    # Initialize the SES client
    ses_client = boto3.client('ses', region_name='us-east-1')  # Adjust region if necessary

    #Construct the email content
    header = f"Here is a summary of the data you submitted, now stored in Assessor.ai ({fn})"
    subject = f"Grader.ai: {subject}"
    body_text = f"{header} {body}\n"
    body_text = body_text.replace('\n', '<br>')
    body_html = f"""
    <html>
    <head></head>
    <body>
        <h1>{subject}</h1>
        <p>{header}</p>
        <p>{body_text}</p>
    </body>
    </html>
    """

    # Email parameters
    sender_email = "compsage@gmail.com"  # Replace with your SES-verified email
    recipient_email = "compsage@gmail.com"  # Email address of the recipient (replace with correct mapping)

    try:
        # Send the email
        response = ses_client.send_email(
            Source=sender_email,
            Destination={'ToAddresses': [recipient_email]},
            Message={
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {
                    'Text': {'Data': body_text, 'Charset': 'UTF-8'},
                    'Html': {'Data': body_html, 'Charset': 'UTF-8'}
                }
            }
        )
        print(f"Email sent successfully! Message ID: {response['MessageId']} {body_text}")
    except NoCredentialsError:
        print("AWS credentials not found.")
    except PartialCredentialsError:
        print("Incomplete AWS credentials provided.")
    except Exception as e:
        print(f"Failed to send email: {e}")

   
