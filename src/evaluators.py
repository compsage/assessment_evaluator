import json
import math
from typing import Any, Dict, List
from gen_ai import GenAI
from abc import ABC, abstractmethod

class Evaluator(ABC):
    def __init__(self, gen_ai: GenAI):
        self.gen_ai = gen_ai
    
    @abstractmethod
    def evaluate(self, answer_key_file: str, quiz_name: str, student_answers: Dict[str, Any]) -> List[str]:
        pass

class AssessmentEvaluator(Evaluator) :
    def evaluate(self, answer_key_file: str, quiz_name: str, student_answers: Dict[str, Any]) -> List[str]:
        # Load answer key file
        with open(answer_key_file, "r", encoding="utf-8") as f:
            answer_keys = json.load(f)
            
        # Load the prompt for the Gen AI to check if the student's answer is equal to the correct answer
        with open("prompts/evaluate_answer.txt", "r", encoding="utf-8") as f:
            answer_evaluation_prompt = f.read()
        
        # Get the specific quiz answer key
        quiz_key = answer_keys.get(quiz_name.lower())
        if quiz_key is None:
            raise ValueError(f"Quiz '{quiz_name}' not found in answer key")
        
        # Retrieve data about the quiz and student
        quiz_name = student_answers.get("name")
        quiz_subject = student_answers.get("subject")
        quiz_section = student_answers.get("section")
        quiz_date = student_answers.get("date")
        student_name = student_answers.get("student_name")
        if student_name is None:
            raise ValueError(f"Student name not found in student answers")
        
        evaluated_quiz = {
            "student_name": student_name,
            "date": quiz_date,
            "name": quiz_name,
            "subject": quiz_subject,
            "section": quiz_section,
            "questions": {}
        }
        
        # Iterate through each question in the student's answers and compare the student's answer to the correct answer
        for student_answers_question_data in student_answers["questions"]:
            question_number = str(student_answers_question_data.get("number"))
            question_text = student_answers_question_data.get("text")
            student_answer = student_answers_question_data.get("student_answer")
            
            answer_key_question_data = quiz_key.get("questions").get(question_number)
            if answer_key_question_data is None:
                raise ValueError(f"Question '{question_number}' not found in answer key for quiz '{quiz_name}'")
                # TODO: Consider handling this even when the question is not found in the answer key
            
            correct_answers = answer_key_question_data.get("answer")
            if correct_answers is None:
                raise ValueError(f"Answer for question '{question_number}' not found in answer key for quiz '{quiz_name}'")
            
            # Check if the question has already been evaluated
            if question_number in evaluated_quiz:
                # TODO: Currently, a ValueError is raised even though it halts the program; In the future, this should be handled more gracefully
                raise ValueError(f"Question '{question_number}' already evaluated")
            
            # Check if the student's answer is in the correct answers; If not, use Gen AI to check if the student's answer is equal
            if student_answer.strip() in correct_answers:
                    evaluated_quiz["questions"][question_number] = {
                        "answer_match": True,
                        "value": answer_key_question_data.get("value"),
                        "correct": True,
                        "partial_credit": False,
                        "comments": "The student's answer correct"
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
                    raise ValueError(f"'correct' is not in the response for question '{question_number}' in quiz '{quiz_name}'\nRaw response: {response}")
                
                # Append the evaluated answer
                evaluated_quiz["questions"][question_number] = {
                    "answer_match": False,
                    "value": answer_key_question_data.get("value"),
                    "correct": correct,
                    "partial_credit": response.get("partial_credit"),
                    "comments": response.get("explanation")
                }
        return evaluated_quiz
        
    # TODO: REFACTOR
    def grade(self, student_assessment):
        correct_answers = []
        partially_correct_answers = []
        partially_correct_diffs = []
        incorrect_answers = []
        overall_points = 0
        total_points = 0
        for answer in student_assessment["checked_answers"]:
            overall_points += answer["value"]
            if answer["answer_match"] :
                total_points += answer["value"]
                correct_answers.append((answer["number"], answer["value"]))
            else :
                #pprint.pprint(answer)
                if "analysis" in answer and answer["analysis"]:
                    if "correct" in answer["analysis"] and answer["analysis"]["correct"] :
                        total_points += answer["value"]
                        correct_answers.append((answer["number"], answer["value"]))
                    elif "partial_credit" in answer["analysis"] and answer["analysis"]["partial_credit"] :
                        add_value = math.ceil(answer["value"]/2)
                        diff_value = (answer["value"] - add_value)
                        total_points += add_value
                        partially_correct_answers.append((answer["number"], math.floor(answer["value"]/2)))
                        partially_correct_diffs.append((answer["number"], diff_value))
                    else :
                        incorrect_answers.append((answer["number"], answer["value"]))
                else :
                    incorrect_answers.append((answer["number"], answer["value"]))

        explanations = ""
        for aq in student_assessment["checked_answers"]:
            if "analysis" in aq and aq["analysis"]:
                explanations += aq["analysis"]["explanation"]
                explanations += "\n"

        kwargs = {"explanations" : explanations}
        performance = self.call_genai(None, "summarize_performance", **kwargs)

        summary = {
            "student_name" : student_assessment["student_name"],
            "date" : student_assessment["date"],
            "name" : student_assessment["name"],
            "subject" : student_assessment["subject"],
            "section" : student_assessment["section"],
            "correct" : correct_answers,
            "incorrect" : incorrect_answers,
            "partially_correct" : partially_correct_answers,
            "partially_correct_diffs" : partially_correct_diffs,
            "grade" : (total_points/overall_points) * 100,
            "total_points" : total_points,
            "overall_points" : overall_points,
            "assessment" : student_assessment["checked_answers"],
            "performance_overview" : performance["overview"]   
            }

        text_summary = self.format(summary)
        summary["text_summary"] = text_summary

        return summary

    def format(self, data):
        # Extract relevant fields from the JSON
        student_name = data.get("student_name", "Unknown")
        assessment_name = data.get("name", "Unknown")
        assessment_subject = data.get("subject", "Unknown")
        date = data.get("date", "Unknown")

        # Prepare lists for correct, partially correct, and incorrect answers
        correct = data.get("correct", [])
        partial = data.get("partially_correct", [])
        partial_diff =  data.get("partially_correct_diffs", [])
        incorrect = data.get("incorrect", [])

        # Extract question numbers as comma-separated strings
        correct_numbers = ", ".join(str(question) for question, _ in correct)
        partial_numbers = ", ".join(str(question) for question, _ in partial)
        incorrect_numbers = ", ".join(str(question) for question, _ in incorrect)

        # Total points for each category
        correct_points = sum(points for _, points in correct)
        partial_points = sum(points for _, points in partial)
        partial_diff = sum(points for _, points in partial_diff)
        incorrect_points = -sum(points for _, points in incorrect)  # Negative for incorrect

        total_points = correct_points + partial_points
        # Overall points and performance overview
        overall_points = data.get("overall_points", 0)
        total_possible_points = correct_points + partial_points - incorrect_points
        performance_percentage = (overall_points / total_possible_points) * 100 if total_possible_points else 0

        # Performance overview
        performance_overview = data.get("performance_overview")

        # Format the output string
        formatted_output = (
            f"Student Name: {student_name}\n"
            f"Date: {date}\n"
            f"Assessment Subject: {assessment_subject}\n"
            f"Assessment Name: {assessment_name}\n\n"
            
            f"Correct Answers: {correct_numbers} ({correct_points} points)\n"
            f"Partially Correct Answers: {partial_numbers} ({partial_points} points, {-partial_diff} points)\n"
            f"Incorrect Answers: {incorrect_numbers} ({incorrect_points} points)\n"
            f"Points Subtracted: {(incorrect_points + -partial_diff)} points\n"
            f"Total Points: {total_points} points\n\n"
            f"{performance_overview}\n"
        )

        return formatted_output