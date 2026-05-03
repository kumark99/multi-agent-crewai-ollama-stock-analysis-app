from crewai import Agent, Task


def create_news_task(agent: Agent, analysis_task: Task, symbol: str) -> Task:
    """
    Task 2 – News research & sentiment analysis assigned to the News Researcher agent.
    Receives analysis_task as context so Agent 2 can reference Agent 1's exact price
    and fundamental metrics for consistency throughout the report.
    """
    return Task(
        name="stock_news_research",
        description=(
            f"Research and analyse all recent news, events, and market sentiment for {symbol}.\n\n"
            "IMPORTANT — CONTEXT CONSISTENCY:\n"
            "The fundamental and technical analysis from Agent 1 is available in your context.\n"
            "You MUST reference the EXACT current price, company name, sector, and analyst consensus\n"
            "values from that analysis — never use different or estimated values.\n\n"
            "STEP 1: Call the 'Get Stock News' tool to fetch the latest news articles.\n"
            "STEP 2: Call the 'Get Market Sentiment' tool for analyst ratings and broader sentiment.\n\n"
            "Cover ALL of the following areas:\n"
            "  1. RECENT NEWS: Top 8–10 most impactful stories — headline, date, source, "
            "     2-sentence summary, market impact (Positive / Negative / Neutral).\n"
            "  2. CORPORATE EVENTS: Earnings, guidance updates, M&A, leadership changes, "
            "     product launches, regulatory actions — include specific dates.\n"
            "  3. ANALYST ACTIVITY: Upgrades/downgrades, price target revisions, "
            "     consensus rating shift — cite analyst/firm names and dates.\n"
            "  4. MACRO & SECTOR CONTEXT: Sector tailwinds/headwinds, macro factors, "
            "     industry trends affecting this specific stock.\n"
            "  5. UPCOMING CATALYSTS: Expected events in the next 30–90 days "
            "     (earnings date, product launches, regulatory decisions).\n"
            "  6. SENTIMENT SCORE: Overall news sentiment score 1–10 with justification.\n\n"
            "Format all tabular data as markdown tables. Use exact dates and source names."
        ),
        expected_output=(
            "A professional, structured news and sentiment report with the following sections.\n\n"
            "## RECENT NEWS SUMMARY\n\n"
            "| # | Headline | Date | Source | Impact |\n"
            "|---|----------|------|--------|--------|\n"
            "| 1 | [headline] | [date] | [source] | Positive/Negative/Neutral |\n"
            "| 2 | [headline] | [date] | [source] | |\n"
            "| … | … | … | … | … |\n\n"
            "For each story provide a 2-sentence summary below the table.\n\n"
            "## CORPORATE EVENTS & CATALYSTS\n\n"
            "| Event | Date | Details | Market Impact |\n"
            "|-------|------|---------|--------------|\n"
            "| [event type] | [date] | [details] | Positive/Negative/Neutral |\n\n"
            "## ANALYST ACTIVITY\n\n"
            "| Analyst / Firm | Action | Previous Target | New Target | Date |\n"
            "|----------------|--------|-----------------|------------|------|\n"
            "| [name] | Upgrade/Downgrade/Reiterate | [price] | [price] | [date] |\n\n"
            "Consensus summary paragraph below the table.\n\n"
            "## MACRO & SECTOR CONTEXT\n\n"
            "Bullet list of 4–6 macro and sector factors with impact assessment.\n\n"
            "## UPCOMING CATALYSTS\n\n"
            "| Catalyst | Expected Date | Potential Impact |\n"
            "|----------|--------------|-----------------|\n"
            "| [event] | [date/quarter] | High/Medium/Low — [brief reason] |\n\n"
            "## NEWS SENTIMENT SCORE\n\n"
            "**Score: [X] / 10** — [3-sentence justification referencing specific stories above]"
        ),
        agent=agent,
        context=[analysis_task],
    )
