import json

def transform_json(data):
    result = {}
    
    for quiz in data:
        quiz_name = quiz['name'].lower()
        # Create a copy of quiz data without 'name' and 'questions'
        quiz_info = {k: v for k, v in quiz.items() if k not in ['name', 'questions']}
        
        # Clean up the section string if it exists
        if 'section' in quiz_info:
            # Replace various dash encodings with a standard dash
            quiz_info['section'] = quiz_info['section'].replace('\u00e2\u20ac\u201c', '–')
        
        # Transform questions into a dictionary with question numbers as keys
        questions = {}
        for q in quiz['questions']:
            questions[str(q['number'])] = {
                'answer': q['answer'],
                'question_text': q['question'],
                'value': q['value']
            }
        
        # Combine quiz info with transformed questions
        quiz_info['questions'] = questions
        result[quiz_name] = quiz_info
    
    return result

# Read the original JSON
with open('data/answer_keys.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Transform the data
transformed_data = transform_json(data)

# Write the transformed JSON with proper encoding
with open('data/transformed_answer_keys.json', 'w', encoding='utf-8') as f:
    json.dump(transformed_data, f, indent=4, ensure_ascii=False)