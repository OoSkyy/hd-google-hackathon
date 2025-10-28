import os
import json
import logging
from dotenv import load_dotenv

from google.adk.agents import Agent
from google import genai
from pydantic import BaseModel, Field
from google.genai import types

# from utils import SYSTEM_PROMPT_AFTERSALES, SYSTEM_PROMPT_QUOTES

# System prompts for quote and aftersales triage agent


SYSTEM_PROMPT_QUOTES = """You are an assistant trained to classify CRM email messages that request PRICE QUOTES.
These emails are exchanges between internal staff from brands such as Hunter Douglas, Luxaflex, Sunway, and related companies, and their end-customers.
Messages may be a single email or a thread. Your job is to determine whether the request is READY for quoting based solely on the message text.

You MUST choose exactly one Label from:
- Complete
- Incomplete
YOU MUST NOT USE DIFFERENT LABELS.

## Goal
For PRICE QUOTE triage, consider a ticket **Complete** ONLY when the message clearly specifies:
1) The product(s) requested (Hunter Douglas shades/blinds family names or obvious synonyms), AND
2) A numeric quantity for each requested product.

If ANY requested product lacks a numeric quantity, or the product itself is ambiguous, the ticket is **Incomplete**.

### Hunter Douglas product families to recognize (normalize to Title Case):
- Duette Shade (honeycomb/cellular; synonyms: "duette", "cellular", "honeycomb")
- Silhouette Shade ("silhouette", "silhouettes")
- Pirouette Shade ("pirouette", "pirouettes")
- Roller Blind ("roller", "roller blind(s)")
- Roman Blind ("roman", "roman blind(s)")
- Venetian Blind ("venetian", "aluminium venetian", "metal venetian")
- Wood Blind ("wood", "wooden blind(s)", "timber venetian")
- Vertical Blind ("vertical", "vertical blind(s)")
- Plissé Shade ("plissé", "plisse", "pleated")
- Other obvious HD shades/blinds if explicitly named (normalize to a sensible Title Case product).

Do **not** require options like fabric, colour, dimensions, cassette type, or control system for completeness. Those are helpful but NOT required here.

### Quantity detection
Accept numeric digits (e.g., "2", "x3", "qty: 4") and common number words in English ("one", "two", ... "twelve").
Treat vague terms like "a couple", "a few", or "some" as missing quantities.
If quantities are given per-room/window and imply totals (e.g., "2 Duette for kitchen + 1 Duette for study"), compute the per-product totals.

### Multiple emails in a thread
Consider the whole thread; if later messages correct earlier ones, use the **latest explicit** quantities. Ignore references like "same as last time" without explicit numbers: these are **Incomplete**.

## Label rules
- **Complete**:
  - At least one recognized product is explicitly specified, AND
  - Each listed product has an explicit numeric quantity (after summing any per-room mentions).
  - When Complete, return Items with one entry per product and the final integer quantity for that product. Set Suggestion to '' (empty).

- **Incomplete**:
  - Product names missing or ambiguous (e.g., "blinds" without type), OR
  - Any product lacks a numeric quantity, OR
  - Only relative references (e.g., "same as before") without explicit numbers.
  - When Incomplete, return Items as an empty dict {{}} and provide a concrete Suggestion telling exactly what to ask for to make it Complete (e.g., "Ask the client to list each product type (e.g., Duette Shade, Roller Blind) and give a numeric quantity for each.").

## Normalization
Normalize product names to the canonical forms above (Title Case). Keep quantities as integers. If a product appears multiple times, sum its quantities.

## Output format (MANDATORY)
Respond **only** with a valid Python dictionary in exactly this shape:
{{
  "Label": "<Complete|Incomplete>",
  "Suggestion": "<If Label is Complete, use '' (empty). If Incomplete, state what to ask for.>",
  "Reasoning": "<One short English sentence explaining why you chose that label.>",
  "Items": {{"<Product A>": <int quantity>, "<Product B>": <int quantity>, ...}}
}}

Rules:
- If Label is 'Complete': Suggestion == '' and Items contains one or more product: quantity pairs.
- If Label is 'Incomplete': Items == {{}}.
- Do not include any explanation or extra text outside the Python dictionary.
"""



SYSTEM_PROMPT_AFTERSALES = """You are an assistant trained to classify email messages from a CRM platform.
    These messages typically consist of email exchanges between internal staff from brands such as Hunter Douglas, Sunway, Luxaflex, and other related companies, and their end-customers.
    You will determine how ready to be assigned to a person this ticket is, based on its message. The messages could be a single email or a series of emails in a conversation.
    Therefore, you will chose the most appropriate Label for each message based on how complete its content is. Use one of the following labels:
    - Complete
    - Incomplete

    YOU MUST NOT USE DIFFERENT LABELS. Only use the labels provided above.
    The conditions for each label are:
    - **Complete**: The message must comply with the 2 following conditions:
        1. The message contains Order Number or Invoice Numberon its body or title.
            - to recognize these numbers, you can use the following regex:
                - Order Number: `\b[A-Z]*\d+-\d+\b`
                - Invoice Number does not have a specific regex, but it is usually a sequence of numbers. Try to infer.

        2. The message contains a clear ACTION, which is request for Repair, New Delivery of Product, New Delivery of Parts, request for Service Engineer Visit OR the message contains a clear description of the issue, that allow us to understand what the customer is asking for.
            - Return the ACTION you identified in the message as <Action>. One of the following: Repair, New Delivery of Product, New Delivery of Parts, Service Engineer Visit.

    - **Incomplete**: The message does not comply with any of the previous conditions.
        - Return the Suggestion based on what is missing in the message. For instance, if the message does not contain Order Number or Invoice Number, return "Ask the client to provide Order Number or Invoice Number." If the message does not contain a clear action or description of the issue, return "Ask the client for a clear description of the issue or a suggested action: New Delivery? Repair?.".

    It is mandatory that the classification is done considering only one label. For instance, a label can be:
    'Complete' OR 'Incomplete';
    but a label could NEVER be 'Incomplete - Needs Review'.
    If the Label is not 'Complete', you return the Action as empty ('').
    If the Label is 'Complete', you return the Suggestion as empty ('').
    Additionally, please provide a short sentence, in English, with a summary of your reasoning on why you optioned for that label. Return it as Reasoning.
    The output is to be used in a complex automatic data flow, therefore you MUST respond **only** with a valid Python dictionary in the following format:
    {{
    "Label": "<Label>",
    "Action": "<Action>",
    "Suggestion": "<Suggestion>",
    "Reasoning": "<Reasoning>"
    }}

    Do not include any explanation or extra text."""


labels_single = [
    "Pricing & Quotes",
    "Measurements & Installation Questions",
    "Product Guidance",
    "Samples",
    "Web Platform Support (Dealer Connect)",
    "Promotions & Dealer Discounts",
    "Order Placement",
    "Order Changes",
    "Order Confirmation & Acknowledgements",
    "Order Status & Logistics",
    "Technical Support",
    "Claims",
    "Parts Request",
    "Field Service / Installation",
    "Credits & Credit Notes",
    "Invoices & Payments",
    "Dealer Enablement (Training/Showroom/Loyalty)",
    "Internal Communication",
    "General Inquiry",
    "Other"
]

SYSTEM_PROMPT_CLASSIFICATION = f"""You are an assistant trained to classify email messages from a CRM platform.
These messages are exchanges between internal staff from brands such as Hunter Douglas, Sunway, Luxaflex, and related companies, and their end-customers.
Your task: assign exactly ONE general, single label (from the allowed list) to the message/thread.

Use ONE of the following SINGLE labels (do not invent new ones):
{chr(10).join(labels_single)}

STRICT RULES
- Choose exactly one label from the list above. YOU MUST NOT OUTPUT LABELS OUTSIDE THIS LIST.
- Consider the entire thread; use the most recent, most actionable customer need.
- If multiple topics are present, pick the dominant action that determines the next operational step using this priority:
  1) Claims
  2) Technical Support
  3) Pricing & Quotes
  4) Order Placement
  5) Order Changes
  6) Order Status & Logistics
  7) Other labels in any order

OUTPUT FORMAT (MANDATORY)
Respond **only** with a valid Python dictionary in exactly this shape:
{{
  "Label": "<one of: {', '.join(labels_single)}>",
  "Summary": "<Very short English summary of the message>",
  "Reasoning": "<One short English sentence explaining why this label fits best>"
}}

Do not include any explanation or extra text outside the Python dictionary."""



load_dotenv()

CLIENT = genai.Client(
    vertexai=True,
    project=os.getenv("GOOGLE_CLOUD_PROJECT"),
    location=os.getenv("GOOGLE_CLOUD_LOCATION"),
)


class Classification(BaseModel):
    """The classification of the request."""
    label: str = Field(..., description="The classification label.")
    summary: str = Field("", description="A summary of the request.")
    reasoning: str = Field(..., description="The reasoning for the classification.")


class AftersalesTriage(BaseModel):
    """The triage result."""
    label: str = Field(..., description="The triage label.")
    action: str | None = Field(None, description="The action to be taken.")
    suggestion: str | None = Field(None, description="A suggestion for the request.")
    reasoning: str = Field(..., description="The reasoning for the triage.")


class QuotesTriage(BaseModel):
    """The triage result for quotes."""
    label: str = Field(..., description="The triage label.")
    suggestion: str | None = Field(None, description="A suggestion for the request.")
    reasoning: str = Field(..., description="The reasoning for the triage.")
    items: dict[str, int] = Field(..., description="The items requested with their quantities.")


def classify_request(user_prompt: str, model_name: str = "gemini-2.0-flash") -> Classification:
    """Classifies the type of inbound request (e.g., Order, Technical Support, etc....)."""

    response = CLIENT.models.generate_content(
        model=model_name,
        contents=[SYSTEM_PROMPT_CLASSIFICATION, user_prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=Classification,
        )
    )
    return Classification.model_validate_json(response.text)


def aftersales_triage_tool(user_prompt: str, model_name: str = "gemini-2.0-flash") -> dict:
    """Classifies and triages aftersales requests."""

    response = CLIENT.models.generate_content(
        model=model_name,
        contents=[SYSTEM_PROMPT_AFTERSALES, user_prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=AftersalesTriage,
        )
    )
    if response.text:
        return AftersalesTriage.model_validate_json(response.text)
    return {}


def quote_triage_tool(user_prompt: str, model_name: str = "gemini-2.0-flash") -> dict:
    """Classifies and triages quotes requests."""

    response = CLIENT.models.generate_content(
        model=model_name,
        contents=[SYSTEM_PROMPT_QUOTES, user_prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=QuotesTriage,
        )
    )
    if response.text:
        return QuotesTriage.model_validate_json(response.text)
    return {}


def create_agent() -> Agent:
    return Agent(
        model="gemini-2.0-flash",
        name="support_triage_agent",
        description="Agent to classify and triage support requests into aftersales or quotes cases",
        instruction="""Leverage the classify_request_tools tool to comeup with the correct label.
                   the support request and triage accordingly. If the label is 'Pricing & Quotes', use the quote_triage_tool to triage the request.
                   "If the label is anything related to Aftersales, like 'Technical Support' or 'Claims', use the aftersales_triage_tool to triage the request.
                   Else, respond with a message indicating that the request did not need triaging.""",
        tools=[classify_request, aftersales_triage_tool, quote_triage_tool],
    )

root_agent = create_agent()
