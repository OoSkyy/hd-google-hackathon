import os
import re

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from google import genai
from google.genai import types
from google.adk.agents import Agent


# Defaults and constants
DEFAULT_MODEL = "gemini-2.0-flash"
AFTERSALES_LABELS = {
    "technical support",
    "claims",
    "parts request",
    "field service / installation",
}
QUOTE_LABELS = {"pricing & quotes", "quotes", "pricing"}
ORDER_REGEX = re.compile(r"\b[A-Z]*\d+-\d+\b")

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

        2. The message contains a clear description of the issue that allows us to understand what the customer is asking for.
            - Do NOT infer a corrective action here. Only capture what the customer explicitly suggests (if any).

    - **Incomplete**: The message does not comply with any of the previous conditions.
        - Return the Suggestion based on what is missing in the message. For instance, if the message does not contain Order Number or Invoice Number, return "Ask the client to provide Order Number or Invoice Number." If the message does not contain a clear action or description of the issue, return "Ask the client for a clear description of the issue or a suggested action: New Delivery? Repair?.".

    It is mandatory that the classification is done considering only one label. For instance, a label can be:
    'Complete' OR 'Incomplete';
    but a label could NEVER be 'Incomplete - Needs Review'.
    If the Label is not 'Complete', you return the ClientActionSuggested as empty ('').
    If the Label is 'Complete', you return the Suggestion as empty ('').
    Additionally, please provide a short sentence, in English, with a summary of your reasoning on why you optioned for that label. Return it as Reasoning.
    The output is to be used in a complex automatic data flow, therefore you MUST respond **only** with a valid Python dictionary in the following format:
    {{
    "Label": "<Label>",
    "ClientActionSuggested": "<Repair|Send New Product|Send New Part of the Product|Send Service Engineer|''>",
    "IssueDescription": "<Short issue description or ''>",
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
    summary: str | None = Field(None, description="A summary of the request.")
    reasoning: str = Field(..., description="The reasoning for the classification.")


class AftersalesTriage(BaseModel):
    """Initial aftersales triage extraction (no action inference)."""
    label: str = Field(..., description="The triage label.")
    client_action_suggested: str | None = Field(None, alias="ClientActionSuggested", description="Action explicitly requested by the customer (not inferred).")
    issue_description: str | None = Field(None, alias="IssueDescription", description="Short description of the issue as stated by the customer.")
    suggestion: str | None = Field(None, description="A suggestion for the request.")
    reasoning: str = Field(..., description="The reasoning for the triage.")


class QuotesTriage(BaseModel):
    """The triage result for quotes."""
    label: str = Field(..., description="The triage label.")
    suggestion: str | None = Field(None, description="A suggestion for the request.")
    reasoning: str = Field(..., description="The reasoning for the triage.")
    items: dict[str, int] = Field(..., description="The items requested with their quantities.")



def classify_request_tools(user_prompt: str, model_name: str = DEFAULT_MODEL) -> dict:
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


def aftersales_triage_tool(user_prompt: str, model_name: str = DEFAULT_MODEL) -> dict:
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


# New: Corrective Action Inference tool for Aftersales
SYSTEM_PROMPT_AFTERSALES_ACTION = """You are a support triage expert.
Given a product context (if known) and a clear issue description, infer the single best corrective action from the allowed list.

Allowed actions:
- Repair
- Send New Product
- Send New Part of the Product
- Send Service Engineer

Instructions
- Choose exactly one action that best addresses the described problem. Please pay attention to the details in the issue description. Try to identify if the product is beyond repair, if parts are missing, or if an on-site visit is needed.
- If the issue description is unclear or missing, set NeedsMoreInfo = true and craft Ask with a concise question to clarify the issue.

Output format (MANDATORY)
Respond **only** with a valid Python dictionary exactly like:
{
  "Action": "<one of the allowed actions>",
  "Reasoning": "<Very short justification>",
  "NeedsMoreInfo": <true|false>,
  "Ask": "<If NeedsMoreInfo is true, a short clarification question; else ''>"
}
"""


class ActionDecision(BaseModel):
    action: str = Field(..., alias="Action", description="Chosen corrective action.")
    reasoning: str = Field(..., alias="Reasoning", description="Short justification.")
    needs_more_info: bool = Field(..., alias="NeedsMoreInfo", description="Whether more information is needed.")
    ask: str = Field(..., alias="Ask", description="Follow-up question if more info is needed.")


def infer_corrective_action_tool(user_prompt: str, model_name: str = DEFAULT_MODEL) -> dict:
    """Infers the corrective action for aftersales given product + issue description."""
    response = CLIENT.models.generate_content(
        model=model_name,
        contents=[SYSTEM_PROMPT_AFTERSALES_ACTION, user_prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ActionDecision,
        ),
    )
    if response.text:
        return ActionDecision.model_validate_json(response.text)
    return {}


def quote_triage_tool(user_prompt: str, model_name: str = DEFAULT_MODEL) -> dict:
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


# --- Consolidation tool: enforce straightforward structured output ---


class ConsolidatedResponse(BaseModel):
    classification_label: str = Field(..., alias="ClassificationLabel")
    aftersales: dict | None = Field(None, alias="Aftersales")
    quote: dict | None = Field(None, alias="Quote")


def _extract_order_number(text: str) -> str | None:
    m = ORDER_REGEX.search(text or "")
    return m.group(0) if m else None


def consolidate_support_triage(user_prompt: str, model_name: str = DEFAULT_MODEL) -> dict:
    """Runs classification, triage, and returns a strict, straightforward JSON with required fields."""
    # 1) Classify
    cls = classify_request_tools(user_prompt, model_name=model_name)
    classification_label = cls["label"] if isinstance(cls, dict) else getattr(cls, "label", "")

    aftersales_out = None
    quote_out = None

    # 2) Branch
    if classification_label.lower() in AFTERSALES_LABELS:
        triage = aftersales_triage_tool(user_prompt, model_name=model_name)
        label = triage.get("label") if isinstance(triage, dict) else getattr(triage, "label", "")

        # Extract values
        order_number = _extract_order_number(user_prompt)
        claim = triage.get("issue_description") if isinstance(triage, dict) else getattr(triage, "issue_description", None)

        corrective_action = None
        if label and label.lower() == "complete" and claim:
            # Infer corrective action using dedicated tool
            action_ctx = f"Product/Context (if any) is in the message. Issue: {claim}"
            action = infer_corrective_action_tool(action_ctx, model_name=model_name)
            corrective_action = action.get("action") if isinstance(action, dict) else getattr(action, "action", None)

        aftersales_out = {
            "OrderNumber": order_number or "",
            "Claim": claim or "",
            "CorrectiveAction": corrective_action or "",
        }

    elif classification_label.lower() in QUOTE_LABELS:
        triage = quote_triage_tool(user_prompt, model_name=model_name)
        items = triage.get("items") if isinstance(triage, dict) else getattr(triage, "items", {})
        # Normalize items dict -> list of {Item, Quantity}
        norm_items = [{"Item": k, "Quantity": int(v)} for k, v in (items or {}).items()]
        quote_out = {
            "Items": norm_items,
        }

    result = ConsolidatedResponse(
        ClassificationLabel=classification_label,
        Aftersales=aftersales_out,
        Quote=quote_out,
    )
    return result.model_dump(by_alias=True)


def create_agent() -> Agent:
    return Agent(
        model=DEFAULT_MODEL,
        name="support_triage_agent",
        description="Agent to classify and triage support requests into aftersales or quotes cases",
        instruction="""Use classify_request_tools to pick the label and route.

If 'Pricing & Quotes':
- Call quote_triage_tool and read its JSON. If Label == 'Incomplete', immediately ask the user for the missing information per the Suggestion field (e.g., product names and numeric quantities). Do not proceed until the user provides. If Label == 'Complete', return the parsed Items and next steps.

If Aftersales (e.g., 'Technical Support', 'Claims'):
- First call aftersales_triage_tool to extract ONLY the client's suggested action (if any) and the issue description (no inference). If Label == 'Incomplete', ask the user to provide a clear description of the issue (symptoms, when it occurs, any error messages) and any identifier (order or invoice); do not infer an action.
- If there is a clear issue description (i.e., Complete), call infer_corrective_action_tool with product (if known) and that description to choose a single corrective action.

Finally, call consolidate_support_triage and respond ONLY with its JSON, which must include:
- ClassificationLabel
- If Aftersales: OrderNumber, Claim, CorrectiveAction
- If Quotes: Items with {Item, Quantity}
""",
        tools=[classify_request_tools, aftersales_triage_tool, infer_corrective_action_tool, quote_triage_tool, consolidate_support_triage],
    )

root_agent = create_agent()
