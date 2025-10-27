from google.adk.agents import Agent

def update_shipment_priority(order_id: str, priority: str) -> dict:
    """Updates the shipment priority for a given order ID."""
    # Placeholder implementation for ERP variant 1
    return {"status": "success", "message": f"Shipment priority for order {order_id} updated to {priority} in ERP 1."}

def get_erp_variant(order_id: str) -> str:
    """Determines the ERP variant for a given order ID."""
    # Placeholder implementation
    return "erp_variant_1"

root_agent = Agent(
    model='gemini-2.5-flash',
    name="erp_sherpa_agent",
    description="Encapsulates knowledge of each ERP variant via tool connectors; translates high-level intents (“update shipment priority”) into correct transactions.",
    tools=[update_shipment_priority],
)