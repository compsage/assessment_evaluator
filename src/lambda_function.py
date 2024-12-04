import boto3
import json
from datetime import datetime
import time
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

from SourceImage import SourceImage
from Processors import Processor
from Evaluator import AssessmentEvaluator

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

    file_path = './data/answer_keys.json'
    with open(file_path, "r", encoding="utf-8") as json_file:
        answers = json.load(json_file)

    #Get the image of the student quiz
    student_quiz_image = SourceImage("./data/quiz1_sample.jpeg")

    image_processor = Processor(prompts_directory="./prompts", openai_api_key=openai_api_key)
    #Call ChatGPT with the image to get the students answers in JSON format
    student_answers = image_processor.call_genai(student_quiz_image, "get_answers_from_student_quiz")
    #pprint.pprint(student_answers)

    #Now that we have the Students answers and the Keys Loaded lets grade it
    assessment_evaluator = AssessmentEvaluator(prompts_directory="./prompts", openai_api_key=openai_api_key)

    #Perform the initial check of the student's quiz against the answer key
    checked_student_answers = assessment_evaluator.check(answers['quiz 1'], student_answers)
    
    #No2 that it's been checked let's grade the exam
    graded_assessment = assessment_evaluator.grade(checked_student_answers)
    
    #Now output the text summary
    text_summary = assessment_evaluator.format(graded_assessment)
    #print(text_summary)

    send_email('None', text_summary)

    return {'status_code' : 201, 'body' : text_summary}

# Get Twilio credentials from AWS Systems Manager Parameter Store
def get_parameter(ssm_client, name):
    try:
        response = ssm_client.get_parameter(Name=name, WithDecryption=True)
        return response['Parameter']['Value']
    except Exception as e:
        print(f"Failed to retrieve parameter {name}: {e}")
        return None

def send_email(fn, body):
    # Initialize the SES client
    ses_client = boto3.client('ses', region_name='us-east-1')  # Adjust region if necessary

    #Construct the email content
    header = f"Here is a summary of the data you submitted, now stored in Assessor.ai ({fn})"
    subject = "Assessor.ai: Data Submission Summary"
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

   
