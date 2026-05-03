from crewai import Agent, LLM

from tools.stock_tools import StockDataTool, TechnicalAnalysisTool


def create_stock_analyst(llm: LLM) -> Agent:
    """Agent 1 – Performs fundamental and technical stock analysis."""
    return Agent(
        role="Senior Stock Market Analyst",
        goal=(
            "Perform a thorough fundamental and technical analysis of the given stock. "
            "Extract key financial metrics, valuation ratios, technical indicators, trend signals, "
            "and provide a data-driven assessment of the stock's current standing."
        ),
        backstory=(
            "You are a seasoned Wall Street analyst with 20+ years of experience at top-tier "
            "investment banks and hedge funds. Your expertise spans equity research, DCF modeling, "
            "and quantitative technical analysis. You are known for your meticulous attention to "
            "detail, data-driven insights, and ability to synthesize complex financial data into "
            "clear, actionable assessments. You have covered thousands of stocks across all sectors "
            "and are adept at spotting value opportunities and risk signals early."
        ),
        tools=[StockDataTool(), TechnicalAnalysisTool()],
        llm=llm,
        verbose=True,
        allow_delegation=False,
        max_iter=8,
    )
