import re
import uvicorn
import sys
import asyncio
from io import StringIO
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

sys.path.append("C:\\Users\\k.bataeva\\Projects\\hd-google-hackathon")


from hd_google_hackathon.agents.support_triage_agent.agent import create_agent as create_support_triage_agent
from hd_google_hackathon.agents.investigation_agent.agent import create_agent as create_investigation_agent
from hd_google_hackathon.agents.policy_compliance_agent.agent import create_agent as create_policy_compliance_agent
from hd_google_hackathon.agents.erp_sherpa_agent.agent import create_agent as create_erp_sherpa_agent
from hd_google_hackathon.agents.playbook_author_agent.agent import create_agent as create_playbook_author_agent
from hd_google_hackathon.agents.metrics_insight_agent.agent import create_agent as create_metrics_insight_agent
from hd_google_hackathon.agents.installer_support_agent.agent import create_agent as create_installer_support_agent
from hd_google_hackathon.agents.configuration_agent.agent import create_agent as create_configuration_agent
from hd_google_hackathon.agents.onboarding_agent.agent import create_agent as create_onboarding_agent

from tests.mocks.mock_order_repository import MockOrderRepository
from tests.mocks.mock_product_repository import MockProductRepository
from tests.mocks.mock_dealer_repository import MockDealerRepository
from tests.mocks.mock_plant_repository import MockPlantRepository
from tests.mocks.mock_component_repository import MockComponentRepository

app = FastAPI()
templates = Jinja2Templates(directory="templates")

MESSAGE_TEMPLATES = {
    "dealer": '''
        <div class="chat-message persona">
            <div class="message-content">{message}</div>
            <div class="timestamp">{timestamp}</div>
        </div>
    ''',
    "system": '''
        <div class="chat-message system">
            <div class="message-content">{message}</div>
            <div class="timestamp">{timestamp}</div>
        </div>
    ''',
    "agent": '''
        <div class="chat-message entity">
            <div class="message-content"><b>{agent_name}:</b> {message}</div>
            <div class="timestamp">{timestamp}</div>
        </div>
    ''',
}

# Create agents
support_triage_agent = create_support_triage_agent()
investigation_agent = create_investigation_agent(order_repo=MockOrderRepository(), component_repo=MockComponentRepository())
policy_compliance_agent = create_policy_compliance_agent()
erp_sherpa_agent = create_erp_sherpa_agent(order_repo=MockOrderRepository())
playbook_author_agent = create_playbook_author_agent()
metrics_insight_agent = create_metrics_insight_agent(dealer_repo=MockDealerRepository(), order_repo=MockOrderRepository(), product_repo=MockProductRepository())
installer_support_agent = create_installer_support_agent(product_repo=MockProductRepository())
configuration_agent = create_configuration_agent()
onboarding_agent = create_onboarding_agent()

import datetime

async def successful_new_order_flow(configuration_agent, runner_wrapper):
    """Runs the successful flow of a new order, from creation to completion."""
    runner = await runner_wrapper(configuration_agent)
    from tests.mocks.mock_order_repository import MockOrderRepository
    order_repository = MockOrderRepository()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    # 1. David (Dealer) places an order for 10 "Duette® Honeycomb Shades".
    yield MESSAGE_TEMPLATES["dealer"].format(message="Dealer 'David' places an order for 10 of product 'ss_duette' (Duette® Honeycomb Shades).", timestamp=timestamp)
    new_order = order_repository.create_order("dealer_1", [{"dealer_product_id": "ss_duette", "quantity": 10}], tenant_id="dealer_1")
    yield MESSAGE_TEMPLATES["system"].format(message=f"Order #{new_order.id} created with status '{new_order.status}'.", timestamp=timestamp)

    # 2. AI Opportunity: Automated Order Validation (Configuration Agent)
    options = {"items": new_order.items}
    prompt = f"Validate configuration with options {options} for tenant 'dealer_1'"

    validation_result = runner.run_and_get_tool_output(prompt, "validate_configuration")
    if validation_result and validation_result.get("valid"):
        yield MESSAGE_TEMPLATES["agent"].format(agent_name="Configuration Agent", message=f"Running validation for order #{new_order.id}... SUCCESS: Configuration is valid.", timestamp=timestamp)
    else:
        yield MESSAGE_TEMPLATES["agent"].format(agent_name="Configuration Agent", message=f"Running validation for order #{new_order.id}... FAILURE: {validation_result.get('reason', 'Unknown reason')}", timestamp=timestamp)
    
    # 3. System updates order status
    order_repository.update_order_status(new_order.id, "in_progress", "dealer_1")
    yield MESSAGE_TEMPLATES["system"].format(message=f"Order #{new_order.id} status updated to 'in_progress'.", timestamp=timestamp)

    # 4. Manufacturing and Shipping
    yield MESSAGE_TEMPLATES["system"].format(message="Manufacturing occurs at the plants...", timestamp=timestamp)
    await asyncio.sleep(1)
    order_repository.update_order_status(new_order.id, "shipped", "dealer_1")
    yield MESSAGE_TEMPLATES["system"].format(message=f"Order #{new_order.id} has been shipped.", timestamp=timestamp)

    # 5. Final delivery and completion
    order_repository.update_order_status(new_order.id, "completed", "dealer_1")
    yield MESSAGE_TEMPLATES["system"].format(message=f"Order #{new_order.id} has been successfully delivered and installed. Status: 'completed'.", timestamp=timestamp)

async def component_out_of_stock_flow(investigation_agent, runner_wrapper):
    """Runs the flow where a component for an order is out of stock, putting the order on hold."""
    runner = await runner_wrapper(investigation_agent)
    from tests.mocks.mock_order_repository import MockOrderRepository
    from tests.mocks.mock_product_repository import MockProductRepository
    order_repository = MockOrderRepository()
    product_repository = MockProductRepository()
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    # 1. David (Dealer) places an order for 5 "Silhouette® Window Shadings".
    yield MESSAGE_TEMPLATES["dealer"].format(message="Dealer 'David' places an order for 5 of product 'ss_silhouette' (Silhouette® Window Shadings).", timestamp=timestamp)
    new_order = order_repository.create_order("dealer_1", [{"dealer_product_id": "ss_silhouette", "quantity": 5}], tenant_id="dealer_1")
    yield MESSAGE_TEMPLATES["system"].format(message=f"Order #{new_order.id} created with status '{new_order.status}'.", timestamp=timestamp)

    # 2. The Investigation Agent checks inventory and finds that fabric_2 is out of stock.
    dealer_product = product_repository.get_dealer_product_by_id(new_order.items[0].dealer_product_id, "dealer_1")
    assert dealer_product is not None
    product = product_repository.get_product_by_id(dealer_product.product_id, "dealer_1")
    assert product is not None
    yield MESSAGE_TEMPLATES["system"].format(message=f"Order requires components: {product.components}", timestamp=timestamp)

    for component_id in product.components:
        prompt = f"Check stock for component '{component_id}' for tenant 'dealer_1'"
        stock_check_result = runner.run_and_get_tool_output(prompt, "check_component_stock")
        stock_level = stock_check_result.get("stock", -1)
        if stock_level == 0:
            yield MESSAGE_TEMPLATES["agent"].format(agent_name="Investigation Agent", message=f"Checking stock for component '{component_id}'... FAILURE: Component is out of stock.", timestamp=timestamp)
            # 3. System puts the order on hold
            order_repository.update_order_status(new_order.id, "on_hold", "dealer_1")
            yield MESSAGE_TEMPLATES["system"].format(message=f"Order #{new_order.id} status updated to 'on_hold'. An alert has been raised for the planner.", timestamp=timestamp)
            break
        else:
            yield MESSAGE_TEMPLATES["agent"].format(agent_name="Investigation Agent", message=f"Checking stock for component '{component_id}'... SUCCESS: {stock_level} units in stock.", timestamp=timestamp)

async def damaged_product_flow(support_triage_agent, investigation_agent, policy_compliance_agent, playbook_author_agent, runner_wrapper):
    """Runs the flow for handling a damaged product claim, involving multiple agents for triage, investigation, compliance, and knowledge capture."""
    support_triage_runner = await runner_wrapper(support_triage_agent)
    investigation_runner = await runner_wrapper(investigation_agent)
    playbook_author_runner = await runner_wrapper(playbook_author_agent)
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    # 1. David (Dealer) creates a new support ticket (Claim).
    dealer_request = "I am filing a claim for order #order_1. The Duette shades arrived damaged. The box was crushed. I need a new delivery of the same product."
    yield MESSAGE_TEMPLATES["dealer"].format(message=f"INCOMING CLAIM from 'David': {dealer_request}", timestamp=timestamp)

    # 2. Automated Triage & Enrichment (Support Triage Agent)
    classification = support_triage_runner.run_and_get_tool_output(f"Classify this request: {dealer_request}", "classify_request_tools")
    yield MESSAGE_TEMPLATES["agent"].format(agent_name="Support Triage Agent", message=f"Intent: '{classification.get('intent', 'Unknown')}'.", timestamp=timestamp)

    # 3. Automated Investigation (Investigation Agent)
    order_history = investigation_runner.run_and_get_tool_output("Pull history for order #order_1", "pull_order_history")
    yield MESSAGE_TEMPLATES["agent"].format(agent_name="Investigation Agent", message=f"Pulling history for order #order_1... SUCCESS: {order_history.get('history', 'Unknown')}", timestamp=timestamp)

    # 5. Automated Knowledge Capture (Playbook Author Agent)
    playbook = playbook_author_runner.run_and_get_tool_output("Summarize case claim_123", "summarize_case")
    yield MESSAGE_TEMPLATES["agent"].format(agent_name="Playbook Author Agent", message=f"{playbook.get('playbook', 'Unknown')}", timestamp=timestamp)

async def proactive_maintenance_flow(metrics_insight_agent, runner_wrapper):
    """Runs the flow for proactive maintenance, where the system predicts a future failure and notifies the dealer."""
    runner = await runner_wrapper(metrics_insight_agent)
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    # 1. The Metrics & Insight Agent monitors product data.
    yield MESSAGE_TEMPLATES["system"].format(message="The Metrics & Insight Agent runs its scheduled analysis of field data.", timestamp=timestamp)

    # 2. The agent identifies a product with a high risk of failure.
    prediction = runner.run_and_get_tool_output("Predict maintenance needs for tenant dealer_1", "predict_maintenance_needs")
    yield MESSAGE_TEMPLATES["agent"].format(agent_name="Metrics & Insight Agent", message=f"ANALYSIS COMPLETE: {prediction.get('prediction', 'Unknown')}", timestamp=timestamp)

    # 3. The agent proactively notifies the dealer.
    yield MESSAGE_TEMPLATES["dealer"].format(message=f"Proactive alert sent to dealer 'David': {prediction.get('recommendation', 'Unknown')}", timestamp=timestamp)

async def complex_product_configuration_flow(configuration_agent, runner_wrapper):
    """Runs the flow for configuring a complex product, including validation and quote generation."""
    runner = await runner_wrapper(configuration_agent)
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    # 1. David (Dealer) needs to order a complex product.
    yield MESSAGE_TEMPLATES["dealer"].format(message="Dealer 'David' starts configuring a complex product.", timestamp=timestamp)
    config_options = {"fabric": "fabric_1", "headrail": "headrail_1", "motorized": True, "quantity": 2}

    # 2. The Configuration Agent guides David through the options.
    validation_result = runner.run_and_get_tool_output(f"Validate configuration with options {config_options} for tenant 'dealer_1'", "validate_configuration")
    if validation_result and validation_result.get("valid"):
        yield MESSAGE_TEMPLATES["agent"].format(agent_name="Configuration Agent", message=f"Validating configuration: {config_options}... SUCCESS: Configuration is valid.", timestamp=timestamp)
        # 3. The agent generates a quote.
        quote = runner.run_and_get_tool_output(f"Generate quote for config {config_options} for tenant 'dealer_1'", "generate_quote")
        yield MESSAGE_TEMPLATES["agent"].format(agent_name="Configuration Agent", message=f"Configuration is valid. Quote: {quote.get('quote', 'Unknown')}", timestamp=timestamp)
        yield MESSAGE_TEMPLATES["dealer"].format(message="Dealer 'David' confirms the order.", timestamp=timestamp)
    else:
        yield MESSAGE_TEMPLATES["agent"].format(agent_name="Configuration Agent", message=f"Validating configuration: {config_options}... FAILURE: {validation_result.get('reason', 'Unknown reason')}", timestamp=timestamp)

async def dealer_onboarding_flow(onboarding_agent, runner_wrapper):
    """Runs the automated onboarding flow for a new dealer."""
    runner = await runner_wrapper(onboarding_agent)
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")

    yield MESSAGE_TEMPLATES["system"].format(message="Executing Flow 7: New Flow - Dealer Onboarding", timestamp=timestamp)

    # 1. A new dealer signs up.
    new_dealer_info = {"name": "Budget Blinds", "region": "USA"}
    yield MESSAGE_TEMPLATES["system"].format(message=f"New dealer has signed up: {new_dealer_info['name']}", timestamp=timestamp)

    # 2. The Onboarding Agent initiates the process.
    yield MESSAGE_TEMPLATES["system"].format(message="AI Opportunity: The Onboarding Agent automates the initial setup.", timestamp=timestamp)
    training = runner.run_and_get_tool_output(f"Provide training materials for dealer: {new_dealer_info}", "provide_training_materials")
    yield MESSAGE_TEMPLATES["agent"].format(agent_name="Onboarding Agent", message=f"{training.get('materials', 'Unknown')}", timestamp=timestamp)

    # 3. The agent sets up the account.
    account_setup = runner.run_and_get_tool_output(f"Set up account for dealer: {new_dealer_info}", "setup_account")
    yield MESSAGE_TEMPLATES["agent"].format(agent_name="Onboarding Agent", message=f"{account_setup.get('message', 'Unknown')}", timestamp=timestamp)

    # 4. The agent schedules a follow-up.
    follow_up = runner.run_and_get_tool_output(f"Schedule follow-up for dealer: {new_dealer_info}", "schedule_follow_up")
    yield MESSAGE_TEMPLATES["agent"].format(agent_name="Onboarding Agent", message=f"{follow_up.get('message', 'Unknown')}", timestamp=timestamp)

    yield MESSAGE_TEMPLATES["system"].format(message="Flow 7 execution complete.", timestamp=timestamp)

flow_mapping = {
    1: (successful_new_order_flow, [configuration_agent]),
    2: (component_out_of_stock_flow, [investigation_agent]),
    3: (damaged_product_flow, [support_triage_agent, investigation_agent, policy_compliance_agent, playbook_author_agent]),
    4: (None, []),
    5: (proactive_maintenance_flow, [metrics_insight_agent]),
    6: (complex_product_configuration_flow, [configuration_agent]),
    7: (dealer_onboarding_flow, [onboarding_agent]),
}

app = FastAPI()
templates = Jinja2Templates(directory="templates")


def get_flows():
    with open("flows.md", "r") as f:
        content = f.read()
    return re.findall(r"## (\d+\..*?):\s(.*?)\n(.*?)(?:### AI Opportunities(.*?))?(?:\n## |\Z)", content, re.DOTALL)


icon_mapping = {
    1: "fa-solid fa-cart-plus",
    2: "fa-solid fa-box-open",
    3: "fa-solid fa-triangle-exclamation",
    4: "fa-solid fa-wrench",
    5: "fa-solid fa-bell",
    6: "fa-solid fa-sliders",
    7: "fa-solid fa-user-plus",
}

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    flows = get_flows()
    tiles = ""
    for flow in flows:
        flow_id = int(flow[0].split(".")[0])
        flow_title = flow[1]
        icon_class = icon_mapping.get(flow_id, "fa-solid fa-question-circle")
        tiles += f'<div class="tile" hx-get="/flow-events/{flow_id}" hx-target="#chat-container" hx-ext="sse"><i class="{icon_class}"></i>{flow_title}</div>'
    return templates.TemplateResponse("index.html", {"request": request, "tiles": tiles})


from google.adk.runners import InMemoryRunner
from google.genai import types

class RunnerWrapper:
    def __init__(self, agent):
        self._agent = agent
        self._runner = None
        self._session = None

    async def setup(self):
        self._runner = InMemoryRunner(agent=self._agent, app_name="agents")
        self._session = await self._runner.session_service.create_session(app_name="agents", user_id="test_user")
        return self

    def run_and_get_tool_output(self, prompt, tool_name):
        if not self._runner or not self._session:
            raise Exception("RunnerWrapper not set up. Call setup() before using.")
        events = []
        for event in self._runner.run(
            user_id=self._session.user_id,
            session_id=self._session.id,
            new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
        ):
            events.append(event)
        
        tool_output = None
        for event in events:
            if isinstance(event, dict):
                return event
            function_responses = event.get_function_responses()
            if function_responses:
                for response in function_responses:
                    if response.name == tool_name:
                        tool_output = response.response
                        break
            if tool_output:
                break
        return tool_output

async def runner_wrapper(agent):
    wrapper = RunnerWrapper(agent)
    await wrapper.setup()
    return wrapper

import json

@app.get("/flow-events/{flow_id}")
async def flow_events(flow_id: int):
    flow_function, agents = flow_mapping.get(flow_id, (None, []))
    if not flow_function:
        return

    async def event_generator():
        flows = get_flows()
        flow_data = next((flow for flow in flows if int(flow[0].split(".")[0]) == flow_id), None)
        if flow_data:
            ai_opportunities = flow_data[3].strip()
            opportunities = re.findall(r"\* \*\*(.*?):\*\* (.*?)(?=\n\*|\Z)", ai_opportunities, re.DOTALL)
            opportunities_html = "".join([f"<li><strong>{title}:</strong> {desc.strip()}</li>" for title, desc in opportunities])
            yield f'data: {json.dumps({"event": "description", "data": f"<h4>AI Opportunities</h4><ul>{opportunities_html}</ul>"})}\n\n'

        async for message in flow_function(*agents, runner_wrapper):
            yield f'data: {json.dumps({"event": "message", "data": message})}\n\n'

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)