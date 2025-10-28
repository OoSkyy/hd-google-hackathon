import pytest
import sys
import time
import asyncio
import ast
import logging

from google.adk.runners import InMemoryRunner
from google.genai import types

from .mocks.mock_order_repository import MockOrderRepository
from .mocks.mock_product_repository import MockProductRepository
from .mocks.mock_dealer_repository import MockDealerRepository
from .mocks.mock_plant_repository import MockPlantRepository
from .mocks.mock_component_repository import MockComponentRepository

from hd_google_hackathon.agents.support_triage_agent.agent import create_agent as create_support_triage_agent
from hd_google_hackathon.agents.investigation_agent.agent import create_agent as create_investigation_agent
from hd_google_hackathon.agents.policy_compliance_agent.agent import create_agent as create_policy_compliance_agent
from hd_google_hackathon.agents.erp_sherpa_agent.agent import create_agent as create_erp_sherpa_agent
from hd_google_hackathon.agents.playbook_author_agent.agent import create_agent as create_playbook_author_agent
from hd_google_hackathon.agents.metrics_insight_agent.agent import create_agent as create_metrics_insight_agent
from hd_google_hackathon.agents.installer_support_agent.agent import create_agent as create_installer_support_agent
from hd_google_hackathon.agents.configuration_agent.agent import create_agent as create_configuration_agent
from hd_google_hackathon.agents.onboarding_agent.agent import create_agent as create_onboarding_agent

logging.basicConfig(level=logging.INFO, format='%(message)s')

# --- Runner Fixture ---

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

@pytest.fixture
def runner_wrapper():
    async def _get_wrapper(agent):
        wrapper = RunnerWrapper(agent)
        await wrapper.setup()
        return wrapper
    return _get_wrapper

# --- Repository Fixtures ---


# --- Agent Fixtures ---

@pytest.fixture
def support_triage_agent():
    return create_support_triage_agent()

@pytest.fixture
def investigation_agent():
    from tests.mocks.mock_order_repository import MockOrderRepository
    from tests.mocks.mock_component_repository import MockComponentRepository
    return create_investigation_agent(
        order_repo=MockOrderRepository(),
        component_repo=MockComponentRepository()
    )

@pytest.fixture
def policy_compliance_agent():
    return create_policy_compliance_agent()

@pytest.fixture
def erp_sherpa_agent():
    from tests.mocks.mock_order_repository import MockOrderRepository
    return create_erp_sherpa_agent(order_repo=MockOrderRepository())

@pytest.fixture
def playbook_author_agent():
    return create_playbook_author_agent()

@pytest.fixture
def metrics_insight_agent():
    from tests.mocks.mock_dealer_repository import MockDealerRepository
    from tests.mocks.mock_order_repository import MockOrderRepository
    from tests.mocks.mock_product_repository import MockProductRepository
    return create_metrics_insight_agent(
        dealer_repo=MockDealerRepository(),
        order_repo=MockOrderRepository(),
        product_repo=MockProductRepository(),
    )

@pytest.fixture
def installer_support_agent():
    from tests.mocks.mock_product_repository import MockProductRepository
    return create_installer_support_agent(product_repo=MockProductRepository())

@pytest.fixture
def configuration_agent():
    return create_configuration_agent()

@pytest.fixture
def onboarding_agent():
    return create_onboarding_agent()

# --- Flow Implementations ---

@pytest.mark.asyncio
async def test_successful_new_order_flow(configuration_agent, runner_wrapper):
    """Tests the successful flow of a new order, from creation to completion."""
    runner = await runner_wrapper(configuration_agent)
    from tests.mocks.mock_order_repository import MockOrderRepository
    order_repository = MockOrderRepository()
    # 1. David (Dealer) places an order for 10 "Duette® Honeycomb Shades".
    logging.info("Dealer 'David' places an order for 10 of product 'ss_duette' (Duette® Honeycomb Shades).")
    new_order = order_repository.create_order("dealer_1", [{"dealer_product_id": "ss_duette", "quantity": 10}], tenant_id="dealer_1")
    logging.info(f"Order #{new_order.id} created with status '{new_order.status}'.")

    # 2. AI Opportunity: Automated Order Validation (Configuration Agent)
    options = {"items": new_order.items}
    prompt = f"Validate configuration with options {options} for tenant 'dealer_1'"

    validation_result = runner.run_and_get_tool_output(prompt, "validate_configuration")
    logging.info(f"[Configuration Agent]: Running validation for order #{new_order.id}..\n{validation_result}")
    
    # 3. System updates order status
    order_repository.update_order_status(new_order.id, "in_progress", "dealer_1")
    logging.info(f"Order #{new_order.id} status updated to 'in_progress'.")

    # 4. Manufacturing and Shipping
    logging.info("Manufacturing occurs at the plants...")
    time.sleep(1)
    order_repository.update_order_status(new_order.id, "shipped", "dealer_1")
    logging.info(f"Order #{new_order.id} has been shipped.")

    # 5. Final delivery and completion
    order_repository.update_order_status(new_order.id, "completed", "dealer_1")
    logging.info(f"Order #{new_order.id} has been successfully delivered and installed. Status: 'completed'.")

@pytest.mark.asyncio
async def test_component_out_of_stock_flow(investigation_agent, runner_wrapper):
    """Tests the flow where a component for an order is out of stock, putting the order on hold."""
    runner = await runner_wrapper(investigation_agent)
    from tests.mocks.mock_order_repository import MockOrderRepository
    from tests.mocks.mock_product_repository import MockProductRepository
    order_repository = MockOrderRepository()
    product_repository = MockProductRepository()
    # 1. David (Dealer) places an order for 5 "Silhouette® Window Shadings".
    logging.info("Dealer 'David' places an order for 5 of product 'ss_silhouette' (Silhouette® Window Shadings).")
    new_order = order_repository.create_order("dealer_1", [{"dealer_product_id": "ss_silhouette", "quantity": 5}], tenant_id="dealer_1")
    logging.info(f"Order #{new_order.id} created with status '{new_order.status}'.")

    # 2. The Investigation Agent checks inventory and finds that fabric_2 is out of stock.
    dealer_product = product_repository.get_dealer_product_by_id(new_order.items[0].dealer_product_id, "dealer_1")
    assert dealer_product is not None
    product = product_repository.get_product_by_id(dealer_product.product_id, "dealer_1")
    assert product is not None
    logging.info(f"Order requires components: {product.components}")

    for component_id in product.components:
        prompt = f"Check stock for component '{component_id}' for tenant 'dealer_1'"
        stock_check_result = runner.run_and_get_tool_output(prompt, "check_component_stock")
        stock_level = stock_check_result.get("stock", -1)
        if stock_level == 0:
            logging.info(f"[Investigation Agent]: Checking stock for component '{component_id}'... FAILURE: Component is out of stock.")
            # 3. System puts the order on hold
            order_repository.update_order_status(new_order.id, "on_hold", "dealer_1")
            logging.info(f"Order #{new_order.id} status updated to 'on_hold'. An alert has been raised for the planner.")
            break
        else:
            logging.info(f"[Investigation Agent]: Checking stock for component '{component_id}'... SUCCESS: {stock_level} units in stock.")

@pytest.mark.asyncio
async def test_damaged_product_flow(support_triage_agent, investigation_agent, policy_compliance_agent, playbook_author_agent, runner_wrapper):
    """Tests the flow for handling a damaged product claim, involving multiple agents for triage, investigation, compliance, and knowledge capture."""
    support_triage_runner = await runner_wrapper(support_triage_agent)
    investigation_runner = await runner_wrapper(investigation_agent)
    policy_compliance_runner = await runner_wrapper(policy_compliance_agent)
    playbook_author_runner = await runner_wrapper(playbook_author_agent)

    # 1. David (Dealer) creates a new support ticket (Claim).
    dealer_request = "I am filing a claim for order #order_1. The Duette shades arrived damaged. The box was crushed. I need a new delivery of the same product."
    logging.info(f"INCOMING CLAIM from 'David': {dealer_request}")

    # 2. Automated Triage & Enrichment (Support Triage Agent)
    classification = support_triage_runner.run_and_get_tool_output(f"Classify this request: {dealer_request}", "classify_request_tools")
    print(f"classification: {classification}")
    logging.info(f"[Support Triage Agent]: Intent: 'Claims'.")

    # 3. Automated Investigation (Investigation Agent)
    order_history = investigation_runner.run_and_get_tool_output("Pull history for order #order_1", "pull_order_history")
    logging.info(f"[Investigation Agent]: Pulling history for order #order_1... SUCCESS: {order_history}")

    # 5. Automated Knowledge Capture (Playbook Author Agent)
    playbook = playbook_author_runner.run_and_get_tool_output("Summarize case claim_123", "summarize_case")
    logging.info(f"[Playbook Author Agent]: {playbook['playbook']}")

@pytest.mark.asyncio
async def test_maintenance_flow(metrics_insight_agent, runner_wrapper):
    """Tests the flow for maintenance, where the system predicts a future failure and notifies the dealer."""
    runner = await runner_wrapper(metrics_insight_agent)
    # 1. The Metrics & Insight Agent monitors product data.
    logging.info("Dealer 'David' wants to check maintenance predictions for his products.")

    # 2. The agent identifies a product with a high risk of failure.
    prediction = runner.run_and_get_tool_output("Predict maintenance needs for product Duette", "predict_maintenance_needs")
    logging.info(f"[Metrics & Insight Agent]: ANALYSIS COMPLETE: {prediction['prediction']}")

    # 3. The agent proactively notifies the dealer.
    logging.info(f"Alert sent to dealer 'David': {prediction['recommendation']}")

@pytest.mark.asyncio
async def test_complex_product_configuration_flow(configuration_agent, runner_wrapper):
    """Tests the flow for configuring a complex product, including validation and quote generation."""
    runner = await runner_wrapper(configuration_agent)
    # 1. David (Dealer) needs to order a complex product.
    logging.info("Dealer 'David' starts configuring a complex product.")
    config_options = {"fabric": "fabric_1", "headrail": "headrail_1", "motorized": True, "quantity": 2}

    # 2. The Configuration Agent guides David through the options.
    validation_result = runner.run_and_get_tool_output(f"Validate configuration with options {config_options} for tenant 'dealer_1'", "validate_configuration")
    logging.info(f"[Configuration Agent]: Validating configuration: {config_options}... {'VALID' if validation_result['valid'] else 'INVALID'}")

    # 3. The agent generates a quote.
    if validation_result['valid']:
        quote = runner.run_and_get_tool_output(f"Generate quote for config {config_options} for tenant 'dealer_1'", "generate_quote")
        logging.info(f"[Configuration Agent]: Configuration is valid. Quote: {quote['quote']}")
        logging.info("Dealer 'David' confirms the order.")
    else:
        logging.info(f"[Configuration Agent]: Configuration is invalid: {validation_result['reason']}")

def test_get_orders_by_dealer():
    """Tests the retrieval of all orders for a specific dealer."""
    from tests.mocks.mock_order_repository import MockOrderRepository
    order_repository = MockOrderRepository()
    # 1. Create a new order for a specific dealer.
    dealer_id = "dealer_2"
    new_order = order_repository.create_order(dealer_id, [{"dealer_product_id": "ss_duette", "quantity": 1}], tenant_id=dealer_id)
    logging.info(f"Order #{new_order.id} created for dealer '{dealer_id}'.")

    # 2. Retrieve all orders for that dealer.
    orders = order_repository.get_orders_by_dealer(dealer_id, tenant_id="any_tenant")
    logging.info(f"Found {len(orders)} orders for dealer '{dealer_id}'.")

    # 3. Verify that the newly created order is in the list.
    assert any(order.id == new_order.id for order in orders)
    logging.info(f"Verified that order #{new_order.id} is in the list of orders for dealer '{dealer_id}'.")


@pytest.mark.asyncio
async def test_dealer_onboarding_flow(onboarding_agent, runner_wrapper):
    """Tests the automated onboarding flow for a new dealer."""
    runner = await runner_wrapper(onboarding_agent)
    logging.info("Executing Flow 7: New Flow - Dealer Onboarding")

    # 1. A new dealer signs up.
    new_dealer_info = {"name": "Budget Blinds", "region": "USA"}
    logging.info(f"New dealer has signed up: {new_dealer_info['name']}")

    # 2. The Onboarding Agent initiates the process.
    logging.info("AI Opportunity: The Onboarding Agent automates the initial setup.")
    training = runner.run_and_get_tool_output(f"Provide training materials for dealer: {new_dealer_info}", "provide_training_materials")
    logging.info(f"[Onboarding Agent]: {training['materials']}")

    # 3. The agent sets up the account.
    account_setup = runner.run_and_get_tool_output(f"Set up account for dealer: {new_dealer_info}", "setup_account")
    logging.info(f"[Onboarding Agent]: {account_setup['message']}")

    # 4. The agent schedules a follow-up.
    follow_up = runner.run_and_get_tool_output(f"Schedule follow-up for dealer: {new_dealer_info}", "schedule_follow_up")
    logging.info(f"[Onboarding Agent]: {follow_up['message']}")

    logging.info("Flow 7 execution complete.")
