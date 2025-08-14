import re
import json

try:
    from config import OPENAI_API_KEY
except Exception:
    import os
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Optional OpenAI client import; only used if API key is present
try:
    from openai import OpenAI  # type: ignore
    _OPENAI_AVAILABLE = True
except Exception:
    _OPENAI_AVAILABLE = False


def update_runtime_openai_key(key: str):
    global OPENAI_API_KEY
    OPENAI_API_KEY = key


def get_ad_parameters_from_ai(description):
    """
    Main function to get ad parameters from a description.
    If OPENAI_API_KEY and openai library are available, uses OpenAI to extract
    structured parameters. Otherwise falls back to the local mock.
    """
    if OPENAI_API_KEY and _OPENAI_AVAILABLE:
        try:
            return _call_openai_for_ad_params(description)
        except Exception:
            # Fallback gracefully if anything goes wrong
            return _mock_ai_processing(description)
    return _mock_ai_processing(description)


def _call_openai_for_ad_params(description):
    """
    Calls OpenAI Chat Completions API to extract structured ad parameters.
    Returns a dict with keys: target_audience, budget, ad_copy
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = (
        "You extract structured Facebook ad parameters from a freeform description. "
        "Return strict JSON with keys: target_audience (string), budget (string), ad_copy (string). "
        "Do not add any commentary."
    )
    user_prompt = (
        "Extract ad parameters (target_audience, budget, ad_copy) from the following description.\n\n"
        f"Description: {description}\n\n"
        "Return JSON only."
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content or "{}"
    parsed = _extract_json(content)

    # Ensure defaults exist
    return {
        "target_audience": parsed.get("target_audience") or "not specified",
        "budget": parsed.get("budget") or "not specified",
        "ad_copy": parsed.get("ad_copy") or description,
    }


def _extract_json(text):
    """Best-effort JSON extraction from a model response that may wrap JSON in code fences."""
    text = text.strip()
    if text.startswith("```"):
        # Remove code fence markers if present
        text = text.strip("`\n")
        # If a language tag is present on the first line, drop it
        if "\n" in text:
            first_line, rest = text.split("\n", 1)
            if first_line.lower().startswith("json"):
                text = rest
            else:
                text = first_line + "\n" + rest
    try:
        return json.loads(text)
    except Exception:
        return {}


def _mock_ai_processing(description):
    """
    A simple mock function to extract ad parameters using regex.
    This simulates the behavior of an AI model for development purposes.
    (Underscore indicates it's a private helper function for this module)
    """
    params = {
        'target_audience': 'not specified',
        'budget': 'not specified',
        'ad_copy': description  # default to full description
    }

    # Example: find budget
    budget_match = re.search(r'(\d+\s*(?:USD|dollars|\$))', description, re.IGNORECASE)
    if budget_match:
        params['budget'] = budget_match.group(1)

    # Example: find audience
    audience_match = re.search(r'for an audience of\s*([\w\s]+)', description, re.IGNORECASE)
    if audience_match:
        potential_audience = audience_match.group(1).strip()
        params['target_audience'] = potential_audience

    # Example: find ad copy
    copy_match = re.search(r'the ad copy should be\s*"(.*?)"', description, re.IGNORECASE)
    if copy_match:
        params['ad_copy'] = copy_match.group(1)

    return params
