import json
import math
from typing import Any, Dict, List
from gen_ai import GenAI

class AssessmentGrader:
    def __init__(self, gen_ai: GenAI):
        self.gen_ai = gen_ai
    
    def _evaluate_assessment(self, answer_key_questions: Dict[str, Any], assessment_name: str, student_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate the student's assessment against the answer key
        
        Args:
            questions (Dict[str, Any]): The questions in the assessment
            assessment_name (str): The name of the assessment
            student_answers (Dict[str, Any]): The student's answers
        
        Returns:
            Dict[str, Any]: The evaluated assessment
        """
            
        # Load the prompt for the Gen AI to check if the student's answer is equal to the correct answer
        with open("prompts/evaluate_answer.txt", "r", encoding="utf-8") as f:
            answer_evaluation_prompt = f.read()
        
        # Retrieve data about the assessment and student
        student_assessment_name = student_answers.get("name")
        student_assessment_subject = student_answers.get("subject")
        student_assessment_section = student_answers.get("section")
        student_assessment_date = student_answers.get("date")
        student_name = student_answers.get("student_name")
        if student_name is None:
            raise ValueError(f"Student name not found in student answers")
        
        evaluated_assessment = {
            "student_name": student_name,
            "date": student_assessment_date,
            "name": student_assessment_name,
            "subject": student_assessment_subject,
            "section": student_assessment_section,
            "questions": {}
        }
        
        # Iterate through each question in the student's answers and compare the student's answer to the correct answer
        for student_answers_question_data in student_answers["questions"]:
            question_number = str(student_answers_question_data.get("number"))
            question_text = student_answers_question_data.get("text")
            student_answer = student_answers_question_data.get("student_answer")
            
            answer_key_question_data = answer_key_questions.get(question_number)
            if answer_key_question_data is None:
                raise ValueError(f"Question '{question_number}' not found in answer key for assessment '{assessment_name}'")
                # TODO: Consider handling this even when the question is not found in the answer key
            
            correct_answers = answer_key_question_data.get("answer")
            if correct_answers is None:
                raise ValueError(f"Answer for question '{question_number}' not found in answer key for assessment '{assessment_name}'")
            
            # Check if the question has already been evaluated
            if question_number in evaluated_assessment:
                # TODO: Currently, a ValueError is raised even though it halts the program; In the future, this should be handled more gracefully
                raise ValueError(f"Question '{question_number}' already evaluated")
            
            # Check if the student's answer is in the correct answers; If not, use Gen AI to check if the student's answer is equal
            if student_answer.strip() in correct_answers:
                    evaluated_assessment["questions"][question_number] = {
                        "answer_match": True,
                        "value": answer_key_question_data.get("value"),
                        "correct": True,
                        "partial_credit": False,
                        "comments": "The student's answer correct" # TODO: Consider adding explanation from Gen AI
                    }
            else:
                # Use Gen AI to check if the student's answer is equal to the correct answer
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
                                    "text": answer_evaluation_prompt.format(key_text=question_text, 
                                                                            key_answer=correct_answers, 
                                                                            student_answer=student_answer)
                                }
                            ]
                        }
                    ],
                    "response_format" : {"type": "json_object"},
                    "max_tokens": 1000,
                    "temperature": 0
                }
    
                # Check if the student's answer is equal to the correct answer using Gen AI
                response = self.gen_ai.request_json(payload=payload)
                
                correct = response.get("correct")
                if correct is None:
                    # TODO: In the future, this should be handled more gracefully so that the program doesn't halt
                    raise ValueError(f"'correct' is not in the response for question '{question_number}' in assessment '{assessment_name}'\nRaw response: {response}")
                
                # Append the evaluated answer
                evaluated_assessment["questions"][question_number] = {
                    "answer_match": False,
                    "value": answer_key_question_data.get("value"),
                    "correct": correct,
                    "partial_credit": response.get("partial_credit"),
                    "comments": response.get("explanation")
                }
        return evaluated_assessment
    
    def _grade_assessment(self, evaluated_assessment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Grade the evaluated assessment by calculating points earned and total percentage
        
        Args:
            evaluated_assessment (Dict[str, Any]): The evaluated assessment containing questions and their results
            
        Returns:
            Dict[str, Any]: The graded assessment with score and percentage
        """
        
        # Load the prompt for the Gen AI to provide an overview of the student's assessment
        with open("prompts/summarize_performance.txt", "r", encoding="utf-8") as f:
            performance_summary_prompt = f.read()
        
        total_points = 0
        earned_points = 0
        
        # Calculate points for each question and build the explanation for the Gen AI
        questions_overview = ""
        for question_number, question_data in evaluated_assessment["questions"].items():
            question_value = question_data.get("value", 0)
            total_points += question_value
            
            # Award points based on correctness
            if question_data.get("correct", False):
                earned_points += question_value
            elif question_data.get("partial_credit", False): 
                earned_points += question_value / 2  # Award 50% for partial credit
                
            questions_overview += f"Question {question_number}: {question_data.get('comments')}\n"
        
        # Calculate percentage grade
        grade_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
        
        # Build the payload for the Gen AI to provide an overview of the student's assessment
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
                            "text": performance_summary_prompt.format(questions_overview=questions_overview)
                        }
                    ]
                }
            ],
            "response_format" : {"type": "json_object"},
            "max_tokens": 2500,
            "temperature": 0
        }

        # Use Gen AI to provide an overview of the student's assessment
        response = self.gen_ai.request_json(payload=payload)
        
        # Add grade information to the assessment
        graded_assessment = evaluated_assessment.copy()
        graded_assessment.update({
            "total_points": total_points,
            "earned_points": earned_points,
            "grade": round(grade_percentage, 1),
            "overview": response.get("overview")
        })
        
        return graded_assessment
    
    def grade(self, answer_key_file: str, assessment_name: str, student_answers: Dict[str, Any]) -> Dict[str, Any]:
        # Load answer key file
        with open(answer_key_file, "r", encoding="utf-8") as f:
            answer_keys = json.load(f)
            
        # Get the specific assessment answer key
        assessment_key_data = answer_keys.get(assessment_name.lower())
        if assessment_key_data is None:
            raise ValueError(f"Assessment '{assessment_name}' not found in answer key")
        answer_key_questions = assessment_key_data.get("questions")
        
        # Evaluate the student's assessment
        evaluated_assessment = self._evaluate_assessment(answer_key_questions=answer_key_questions,
                                                         assessment_name=assessment_name, 
                                                         student_answers=student_answers)
                
        # Grade the student's assessment
        graded_assessment = self._grade_assessment(evaluated_assessment=evaluated_assessment)

        return graded_assessment