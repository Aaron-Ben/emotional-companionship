import re


def extract_json(text: str) -> str:
    """
    Extracts JSON content from a string, removing enclosing triple backticks
    and optional 'json' tag if present.
    If no code block is found, returns the text as-is.

    Args:
        text: The text to extract JSON from

    Returns:
        The extracted JSON string

    Examples:
        >>> extract_json('```json\\n{"key": "value"}\\n```')
        '{"key": "value"}'
        >>> extract_json('{"key": "value"}')
        '{"key": "value"}'
    """
    text = text.strip()
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        json_str = text  # assume it's raw JSON
    return json_str
