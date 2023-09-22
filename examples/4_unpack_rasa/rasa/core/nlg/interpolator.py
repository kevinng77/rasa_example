import re
import logging
from typing import Text, Dict, Union, Any, List

logger = logging.getLogger(__name__)


def interpolate_text(response: Text, values: Dict[Text, Text]) -> Text:
    """Interpolate values into responses with placeholders.

    Transform response tags from "{tag_name}" to "{0[tag_name]}" as described here:
    https://stackoverflow.com/questions/7934620/python-dots-in-the-name-of-variable-in-a-format-string#comment9695339_7934969
    Block characters, making sure not to allow:
    (a) newline in slot name
    (b) { or } in slot name

    Args:
        response: The piece of text that should be interpolated.
        values: A dictionary of keys and the values that those
            keys should be replaced with.

    Returns:
        The piece of text with any replacements made.
    """
    try:
        text = re.sub(r"{([^\n{}]+?)}", r"{0[\1]}", response)
        text = text.format(values)
        if "0[" in text:
            # regex replaced tag but format did not replace
            # likely cause would be that tag name was enclosed
            # in double curly and format func simply escaped it.
            # we don't want to return {0[SLOTNAME]} thus
            # restoring original value with { being escaped.
            return response.format({})

        return text
    except KeyError as e:
        logger.exception(
            f"Failed to replace placeholders in response '{response}'. "
            f"Tried to replace '{e.args[0]}' but could not find "
            f"a value for it. There is no slot with this "
            f"name nor did you pass the value explicitly "
            f"when calling the response. Return response "
            f"without filling the response. "
        )
        return response


def interpolate(
    response: Union[List[Any], Dict[Text, Any], Text], values: Dict[Text, Text]
) -> Union[List[Any], Dict[Text, Any], Text]:
    """Recursively process response and interpolate any text keys.

    Args:
        response: The response that should be interpolated.
        values: A dictionary of keys and the values that those
            keys should be replaced with.

    Returns:
        The response with any replacements made.
    """
    if isinstance(response, str):
        return interpolate_text(response, values)
    elif isinstance(response, dict):
        for k, v in response.items():
            if isinstance(v, dict):
                interpolate(v, values)
            elif isinstance(v, list):
                response[k] = [interpolate(i, values) for i in v]
            elif isinstance(v, str):
                response[k] = interpolate_text(v, values)
        return response
    elif isinstance(response, list):
        return [interpolate(i, values) for i in response]
    return response
