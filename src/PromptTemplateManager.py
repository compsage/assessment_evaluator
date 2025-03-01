import os

class TemplateFormatException(Exception):
    """
    Exception raised when a template is not formatted correctly.
    """
    pass

class PromptTemplateManager:
    """
    Class to manage templates.
    """

    def __init__(self, templates_directory="./prompt_templates"):
        """
        Initializes the PromptTemplateManager and loads template files from the specified directory.


        :param templates_directory: Path to the directory containing .template and .json-schema files.
        """
        self.templates = self._load_templates_recursively(templates_directory)

    def _load_templates_recursively(self, directory):
        """
        Recursively loads all .template and .json-schema files from the given directory into a dictionary.

        :param directory: Path to the directory containing .template and .json-schema files.
        :return: Dictionary with filenames (without extension) as keys and dictionaries containing 'template' and 'schema' as values.
        """
        templates = {}
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith(".template.txt") or filename.endswith(".schema.json"):
                    filepath = os.path.join(root, filename)
                    key = os.path.relpath(filepath, directory).replace(os.sep, "/").rsplit(".", 2)[0]
                    
                    if key not in templates:
                        templates[key] = {"template": None, "schema": None}

                    with open(filepath, "r", encoding="utf-8") as file:
                        content = file.read()

                    if filename.endswith(".template.txt"):
                        templates[key]["template"] = content
                    elif filename.endswith(".schema.json"):
                        templates[key]["schema"] = content

        return templates

    def get_template(self, key):
        """
        Retrieves a template by key.

        :param key: The key of the desired template.
        :return: A dictionary containing 'template' and 'schema', or None if not found.
        """
        return self.templates.get(key)

    def list_templates(self):
        """
        Lists all available template keys.

        :return: A list of template keys.
        """
        return list(self.templates.keys())

    def format_template(self, key, **kwargs):
        """
        Formats a specific template with the given keyword arguments.

        :param key: The key of the template to format.
        :param kwargs: The variables to format into the template.
        :return: The formatted template string.
        :raises TemplateFormatException: If the template cannot be formatted correctly.
        """
        if key not in self.templates or not self.templates[key]["template"]:
            raise TemplateFormatException(f"Template with key '{key}' not found.")

        try:
            formatted_template = self.templates[key]["template"].format(**kwargs)
            return formatted_template
        except KeyError as e:
            raise TemplateFormatException(f"Missing required placeholder for formatting: {e}")
        except Exception as e:
            raise TemplateFormatException(f"Error formatting template: {e}")

    def display_template_details(self, key):
        """
        Displays the template and schema of a template and lists the required variables.

        :param key: The key of the template to display.
        :raises TemplateFormatException: If the template is not found.
        """
        if key not in self.templates:
            raise TemplateFormatException(f"Template with key '{key}' not found.")

        template = self.templates[key].get("template")
        schema = self.templates[key].get("schema")

        print(f"Template for '{key}':\n{template}\n" if template else f"No template found for '{key}'.")
        print(f"Schema for '{key}':\n{schema}\n" if schema else f"No schema found for '{key}'.")

        if template:
            placeholders = [word.strip("{}") for word in template.split() if word.startswith("{") and word.endswith("}")]
            print("--------------------------------------")
            print(f"Required Variables: {placeholders}\n")

# Example usage
if __name__ == "__main__":
    manager = PromptTemplateManager("../prompt_templates")
    print("Loaded Templates:", manager.list_templates())
    example_key = manager.list_templates()[0] if manager.list_templates() else None
    if example_key:
        print(f"Details of '{example_key}':")
        manager.display_template_details(example_key)

        try:
            formatted = manager.format_template(example_key, name="John", action="test")
            print(f"Formatted Template:\n{formatted}")
        except TemplateFormatException as e:
            print(f"Error: {e}")
