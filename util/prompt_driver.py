import os
import re


class PromptManager:
    def __init__(self, directory_path):
        """
        Initialize the PromptManager and load all prompt templates from the directory.
        """
        self.prompts = {}
        self._load_prompts(directory_path)

    def _load_prompts(self, directory_path):
        """
        Reads all `.txt` files in the directory and stores them in a dictionary.
        The key is the filename without the '.txt' extension, and the value is a dictionary
        containing the template and the list of required variables.
        """
        if not os.path.isdir(directory_path):
            raise ValueError(f"The directory {directory_path} does not exist or is not a directory.")

        for filename in os.listdir(directory_path):
            if filename.endswith(".txt"):
                key = filename[:-4]  # Remove ".txt"
                with open(os.path.join(directory_path, filename), "r") as file:
                    template = file.read()
                    required_values = self._extract_required_values(template)
                    self.prompts[key] = {"template": template, "required": required_values}

    def _extract_required_values(self, template):
        """
        Extracts and returns the list of required variables from a template string.
        Looks for placeholders in the format `{placeholder_name}`.
        """
        return re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template)

    def render_prompt(self, prompt_name, **kwargs):
        """
        Renders a prompt template with the provided keyword arguments.
        If the prompt or template variables are missing, raise an exception
        that includes the required values.
        """
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found in loaded templates.")

        prompt_data = self.prompts[prompt_name]
        template = prompt_data["template"]
        required_values = prompt_data["required"]

        # Validate that all required values are provided
        missing_keys = [key for key in required_values if key not in kwargs]
        if missing_keys:
            raise ValueError(
                f"Missing required variables {missing_keys} for the prompt '{prompt_name}'.\n"
                f"Required values: {required_values}\n"
                f"Provided values: {list(kwargs.keys())}"
            )

        # Render the prompt or return the raw template if no kwargs are provided
        return template.format(**kwargs) if kwargs else template

    def get_prompt(self, prompt_name):
        """
        Returns the raw template string for a specific prompt.
        """
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found in loaded templates.")
        return self.prompts[prompt_name]["template"]

    def get_prompt_data(self, prompt_name):
        """
        Returns the full dictionary (template and required values) for a specific prompt.
        """
        if prompt_name not in self.prompts:
            raise ValueError(f"Prompt '{prompt_name}' not found in loaded templates.")
        return self.prompts[prompt_name]

    def get_all_prompts(self):
        """
        Returns the entire dictionary of prompts.
        """
        return self.prompts

    def list_prompt_names(self):
        """
        Lists all prompt names available in the dictionary.
        """
        return list(self.prompts.keys())

    def list_all_prompts_with_required_values(self):
        """
        Prints all prompt names along with their required variables.
        """
        for name, data in self.prompts.items():
            print(f"Prompt Name: {name}")
            print(f"Required Values: {data['required']}\n")


if __name__ == "__main__":
    # Initialize the PromptManager
    prompt_manager = PromptManager("../prompts")

    # List all prompts with required values
    prompt_manager.list_all_prompts_with_required_values()

    # Render a prompt correctly
    print(prompt_manager.render_prompt("get_questions_answers_from_key"))

    # Get the raw template for a specific prompt
    print(prompt_manager.get_prompt("get_questions_answers_from_key"))

    # Get the full dictionary for a specific prompt
    print(prompt_manager.get_prompt_data("get_questions_answers_from_key"))

    # Get the entire dictionary of prompts
    print(prompt_manager.get_all_prompts())
