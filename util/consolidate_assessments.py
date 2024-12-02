import os
import json
from collections import defaultdict

# Directory containing the JSON files
directory = "../data/all_answer_key_images"

# Resultant dictionary
aggregated_data = defaultdict(lambda: {"questions": []})

# Loop through all files in the directory
for filename in os.listdir(directory):
    if filename.endswith(".json"):
        file_path = os.path.join(directory, filename)
        
        # Load the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
        
        if not data:
            continue

        # Extract the name and questions fields
        name = data.get("name", "").lower()
        questions = data.get("questions", [])
        
        if name:
            # Extend the questions list for the current name
            aggregated_data[name]["questions"].extend(questions)

# Convert back to a regular dictionary (if needed)
final_data = dict(aggregated_data)

# Example: Save the result to a file
output_path = "../data/aggregated_answer_data.json"
with open(output_path, 'w') as output_file:
    json.dump(final_data, output_file, indent=4)

print(f"Aggregated data has been saved to {output_path}")
