from google.adk.agents import Agent
from hd_google_hackathon.config import DEFAULT_MODEL
from hd_google_hackathon.data.repositories.dealer_repository import DealerRepository
from hd_google_hackathon.data.repositories.order_repository import OrderRepository
from hd_google_hackathon.data.repositories.product_repository import ProductRepository
from hd_google_hackathon.data.repositories.sqlite.dealer_repository import SqliteDealerRepository
from hd_google_hackathon.data.repositories.sqlite.order_repository import SqliteOrderRepository
from hd_google_hackathon.data.repositories.sqlite.product_repository import SqliteProductRepository
from random import randint

def surface_systemic_issues() -> dict:
    """Surfaces systemic issues from a collection of resolved cases."""
    return {"issues": ["Systemic Risk: Component 'CPU-001' has caused 5 order delays this week. Flagging for supply chain review."]}

def predict_maintenance_needs(product_id: str) -> dict:
    """Analyzes historical data to predict future maintenance needs for a given product."""
    # In a real system, this would analyze real usage and failure data.
    # For this simulation, we'll return a hardcoded prediction.
    return {
        "prediction": f"Product '{product_id}' has a {randint(5, 30)}% probability of chain failure in the next {randint(1, 6)} months based on usage patterns.",
        "recommendation": "Proactively send replacement chain_2 and schedule maintenance."
    }

def give_overview(dealer_repo: DealerRepository, order_repo: OrderRepository, product_repo: ProductRepository) -> dict:
    """Gives an overview of the available data repositories. And provides information about dealers, orders, and products. including Id's, names, parts etc."""
    return {
        "status": "success",
        "overview": {
            "dealers": dealer_repo.get_all_dealers(),
            "orders": order_repo.get_all_orders(),
            "products": product_repo.get_products()
        }
    }

def provide_insights(dealer_repo: DealerRepository, order_repo: OrderRepository, product_repo: ProductRepository) -> dict:
    """Provides data-driven insights to support business decisions."""
    try:
        products = product_repo.get_products()
        dealers = dealer_repo.get_all_dealers()
        insights = []
        if not products:
            insights.append("No products found in the mock DB.")
        else:
            insights.append(f"Found {len(products)} products; top sample: {products[0].name}")

        for dealer in dealers:
            orders = order_repo.get_orders_for_dealer(dealer.id)
            insights.append(f"Dealer {dealer.name} has {len(orders)} orders in the mock DB.")

        return {"status": "success", "insights": insights}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def compute_dealer_insights(dealer_id: str, dealer_repo: DealerRepository) -> dict:
    """ADK tool: Compute simple insights for a given dealer id.

    The function is read-only and will try multiple ID normalizations (dash/underscore)
    and fallback to name matching. It returns counts and top products.
    """
    return dealer_repo.get_dealer_insights(dealer_id)

def create_agent(
    dealer_repo: DealerRepository,
    order_repo: OrderRepository,
    product_repo: ProductRepository,
) -> Agent:
    def provide_insights_tool() -> dict:
        return provide_insights(
            dealer_repo=dealer_repo,
            order_repo=order_repo,
            product_repo=product_repo,
        )

    def compute_dealer_insights_tool(dealer_id: str) -> dict:
        return compute_dealer_insights(
            dealer_id=dealer_id,
            dealer_repo=dealer_repo,
        )
    
    def give_overview_tool() -> dict:
        return give_overview(
            dealer_repo=dealer_repo,
            order_repo=order_repo,
            product_repo=product_repo,
        )

    provide_insights_tool.__name__ = "provide_insights"
    compute_dealer_insights_tool.__name__ = "compute_dealer_insights"
    give_overview_tool.__name__ = "give_overview"

    return Agent(
        name="metrics_insight_agent",
        model=DEFAULT_MODEL,
        description="""Synthesizes operational KPIs, surfacing systemic issues (e.g., recurring part shortages or dealer training gaps), and predicts maintenance needs from historical data.
        when you dont know about a product's maintenance history or usage patterns, this agent can help fill in the gaps with data-driven insights.
        
        when someone asks you a question, always try to answer with the most relevant information you have.
        If you don't have the information, say you don't know.
        
        You are a Metrics Insight Agent that provides data-driven insights to support business decisions.
        Use the tools at your disposal to analyze historical data, identify trends, and generate actionable recommendations.
        Always consider the context of the business and the specific needs of the stakeholders when providing insights.

        Path 1: Surface systemic issues from resolved cases to identify recurring problems and areas for improvement.
            use the tool 'surface_systemic_issues' to do this.
            ask the user for more information about the issues they are facing.
        Path 2: Predict future maintenance needs for products based on historical usage and failure data to enable proactive maintenance planning.
            use the tool 'predict_maintenance_needs' to do this.
            ask the user for the product id they want to analyze.
        Path 3: Provide an overview of the available data points, including dealers, orders, and products.
            use the tool 'give_overview' to do this.
            ask the user for the specific repository they want to know about.
        Path 4: Compute simple insights for a given dealer id
            use the tool 'compute_dealer_insights' to do this.
            ask the user for the dealer id they want insights about.""",
        tools=[
            surface_systemic_issues,
            predict_maintenance_needs,
            provide_insights_tool,
            give_overview_tool,
            compute_dealer_insights_tool,
        ],
    )

dealer_repo = SqliteDealerRepository()
order_repo = SqliteOrderRepository()
product_repo = SqliteProductRepository()

root_agent = create_agent(
    dealer_repo=dealer_repo,
    order_repo=order_repo,
    product_repo=product_repo,
)
