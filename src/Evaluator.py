
from Processors import Processor
import math

class AssessmentEvaluator(Processor) :
    def process(self):
        print("Process Method...")

    def check(self, answer_key, student_assessment) :
        ql = []
        output = []
        for correct_answer in answer_key['questions'] :
            for student_answer in student_assessment['questions'] :
                if correct_answer['number'] == student_answer['number'] :
                    if student_answer['student_answer'] in correct_answer['answer'] :
                        ql.append({**correct_answer, **student_answer, 'answer_match' : True})
                        output.append({**correct_answer, **student_answer, 'answer_match' : True})
                    else :
                        ql.append({**correct_answer, **student_answer, 'answer_match' : False})
    

        for answer in ql :
            if answer['answer_match'] :
                continue
            
            values = {  'key_text': answer['text'], 
                        'key_answer' : answer['answer'], 
                        'student_answer' : answer['student_answer']
                    }

            analysis_output = self.call_genai(None, 'evaluate_answer', **values)
            output.append({**answer, 'analysis' : analysis_output})

        student_assessment['checked_answers'] = output
        return student_assessment
    
    def grade(self, student_assessment) :
        correct_answers = []
        partially_correct_answers = []
        partially_correct_diffs = []
        incorrect_answers = []
        overall_points = 0
        total_points = 0
        for answer in student_assessment['checked_answers']:
            overall_points += answer['value']
            if answer['answer_match'] :
                total_points += answer['value']
                correct_answers.append((answer['number'], answer['value']))
            else :
                #pprint.pprint(answer)
                if 'analysis' in answer and answer['analysis']:
                    if 'correct' in answer['analysis'] and answer['analysis']['correct'] :
                        total_points += answer['value']
                        correct_answers.append((answer['number'], answer['value']))
                    elif 'partial_credit' in answer['analysis'] and answer['analysis']['partial_credit'] :
                        add_value = math.ceil(answer['value']/2)
                        diff_value = (answer['value'] - add_value)
                        total_points += add_value
                        partially_correct_answers.append((answer['number'], math.floor(answer['value']/2)))
                        partially_correct_diffs.append((answer['number'], diff_value))
                    else :
                        incorrect_answers.append((answer['number'], answer['value']))
                else :
                    incorrect_answers.append((answer['number'], answer['value']))

        explanations = ''
        for aq in student_assessment['checked_answers'] :
            if 'analysis' in aq and aq['analysis'] :
                explanations += aq['analysis']['explanation']
                explanations += '\n'

        kwargs = {'explanations' : explanations}
        performance = self.call_genai(None, 'summarize_performance', **kwargs)

        summary = {
            'student_name' : student_assessment['student_name'],
            'date' : student_assessment['date'],
            'name' : student_assessment['name'],
            'subject' : student_assessment['subject'],
            'section' : student_assessment['section'],
            'correct' : correct_answers,
            'incorrect' : incorrect_answers,
            'partially_correct' : partially_correct_answers,
            'partially_correct_diffs' : partially_correct_diffs,
            'grade' : (total_points/overall_points) * 100,
            'total_points' : total_points,
            'overall_points' : overall_points,
            'assessment' : student_assessment['checked_answers'],
            'performance_overview' : performance['overview']   
            }

        text_summary = self.format(summary)
        summary['text_summary'] = text_summary

        return summary

    def format(self, data):
        # Extract relevant fields from the JSON
        student_name = data.get('student_name', 'Unknown')
        assessment_name = data.get('name', 'Unknown')
        assessment_subject = data.get('subject', 'Unknown')
        date = data.get('date', 'Unknown')

        # Prepare lists for correct, partially correct, and incorrect answers
        correct = data.get('correct', [])
        partial = data.get('partially_correct', [])
        partial_diff =  data.get('partially_correct_diffs', [])
        incorrect = data.get('incorrect', [])

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
        overall_points = data.get('overall_points', 0)
        total_possible_points = correct_points + partial_points - incorrect_points
        performance_percentage = (overall_points / total_possible_points) * 100 if total_possible_points else 0

        # Performance overview
        performance_overview = data.get('performance_overview')

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