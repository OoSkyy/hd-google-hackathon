FLOWS = [
    {
        "id": 1,
        "title": "Successful Flow: New Order and Installation",
        "description": "This flow describes the ideal scenario from placing an order to successful installation.",
        "ai_opportunities": [
            {
                "title": "Conversational Ordering (Interaction Hub)",
                "description": "An AI agent within the **Interaction Hub** could allow `David` to place orders using natural language."
            },
            {
                "title": "Automated Order Validation (Investigation Agent)",
                "description": "A specialized **`Investigation Agent`** can automate the review process. It would query the **`Knowledge Graph`** to verify component dependencies and the **`Federated Integration Mesh`** to check real-time inventory in the ERP, freeing up the planner to focus on exceptions."
            },
            {
                "title": "Proactive Status Updates (Interaction Hub)",
                "description": "An agent can proactively push real-time status updates from the manufacturing and logistics systems (via the **`Federated Integration Mesh`**) to the dealer's workspace in the **Interaction Hub**."
            }
        ]
    },
    {
        "id": 2,
        "title": "Failure Flow: Component Out of Stock",
        "description": "This flow describes what happens when a component is not available.",
        "ai_opportunities": [
            {
                "title": "Intelligent Dealer Communication (Interaction Hub)",
                "description": "An agent in the **Interaction Hub** can automate the notification. It would inform `David` about the delay (data from the **`Federated Integration Mesh`**) and query the **`Knowledge Graph`** to suggest alternative branded products that are in stock and can be shipped immediately."
            }
        ]
    },
    {
        "id": 3,
        "title": "Failure Flow: Damaged Product on Arrival",
        "description": "This flow describes the process for handling a product that arrives damaged.",
        "ai_opportunities": [
            {
                "title": "Guided Claims Intake (Interaction Hub)",
                "description": "A conversational agent in the **Interaction Hub** guides `David` through the submission, ensuring all necessary information is collected upfront."
            },
            {
                "title": "Automated Triage & Resolution (Support Triage & Investigation Agents)",
                "description": "A **`Support Triage Agent`** first classifies and enriches the incoming claim. It then triggers an **`Investigation Agent`** that queries the **`Knowledge Graph`** for order history and uses the **`Vector Store`** to compare the claim description against past cases. If the claim is within policy (checked by a **`Policy & Compliance Agent`**), it can automatically initiate a replacement. The entire resolution is then passed to a **`Playbook Author Agent`** to create a new playbook if the case is novel."
            }
        ]
    },
    {
        "id": 4,
        "title": "Failure Flow: Installation Issue",
        "description": "This flow describes how to handle an issue during the installation process.",
        "ai_opportunities": [
            {
                "title": "On-Site Installer Support (Knowledge Services)",
                "description": "An **'Installer Support Agent'** can be the first line of support. It uses the **`Vector Store`** to find solutions in installation manuals and the **`Knowledge Graph`** to understand the product's component dependencies. If the issue is new, the resolution is captured and sent to a **`Playbook Author Agent`** to enrich the knowledge base for future incidents."
            }
        ]
    },
    {
        "id": 5,
        "title": "New Flow: Proactive Maintenance Alert",
        "description": "This flow describes how AI can predict and prevent product failures.",
        "ai_opportunities": [
            {
                "title": "Predictive Lifecycle Management (Metrics & Insight Agent)",
                "description": "A specialized **`Metrics & Insight Agent`** analyzes historical data from the **`Knowledge Graph`** and long-term episodic memory. By identifying systemic issues, it can predict failures, improving customer experience and preventing costly, urgent failures."
            }
        ]
    },
    {
        "id": 6,
        "title": "New Flow: Complex Product Configuration",
        "description": "This flow describes how AI can assist in ordering highly customized products.",
        "ai_opportunities": [
            {
                "title": "Guided Configuration (Interaction Hub & Knowledge Graph)",
                "description": "A **'Configuration Agent'** acts as an expert assistant within the **Interaction Hub**. It uses the **`Knowledge Graph`** to understand complex product compatibility rules and dependencies, preventing configuration errors and reducing the need for support calls."
            }
        ]
    },
    {
        "id": 7,
        "title": "New Flow: Dealer Onboarding",
        "description": "This flow describes how to efficiently onboard a new dealer.",
        "ai_opportunities": [
            {
                "title": "Automated Onboarding (Interaction Hub & Vector Store)",
                "description": "An **'Onboarding Agent'** in the **Interaction Hub** automates the initial setup. It provides a consistent, guided experience by pulling personalized training materials from the **`Vector Store`**. This allows `Michael` (Account Manager) to focus his time on relationship-building rather than on administrative tasks."
            }
        ]
    }
]
