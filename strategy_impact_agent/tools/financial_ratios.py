import os
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field


class FinancialRatios(BaseTool):
    """
    Compute standard nonprofit financial health indicators from uploaded or pasted
    financial data (990, budget actuals, or financial statements).

    Indicators computed:
    - Program expense ratio (program expenses / total expenses)
    - Fundraising efficiency (fundraising expenses / total contributions)
    - Administrative ratio (admin expenses / total expenses)
    - Months of operating cash (unrestricted net assets / monthly expenses)
    - Revenue diversification index (Herfindahl-Hirschman Index)
    - Net asset trend (year-over-year)

    Use before producing financial analysis for board presentations, sustainability
    assessments, or consulting client capacity assessments.

    Accepts data as named keyword arguments (paste from 990 or budget).
    """

    total_revenue: Optional[float] = Field(None, description="Total revenue for the period")
    total_expenses: Optional[float] = Field(None, description="Total expenses for the period")
    program_expenses: Optional[float] = Field(
        None, description="Program service expenses (from 990 Part IX)"
    )
    management_expenses: Optional[float] = Field(
        None, description="Management and general expenses"
    )
    fundraising_expenses: Optional[float] = Field(
        None, description="Fundraising expenses"
    )
    total_contributions: Optional[float] = Field(
        None, description="Total contributions, gifts, and grants received"
    )
    unrestricted_net_assets: Optional[float] = Field(
        None, description="Unrestricted net assets (end of period)"
    )
    prior_year_net_assets: Optional[float] = Field(
        None, description="Total net assets from prior year (for trend)"
    )
    current_year_net_assets: Optional[float] = Field(
        None, description="Total net assets current year"
    )
    revenue_sources: Optional[dict] = Field(
        None,
        description=(
            "Revenue by source for diversification analysis. "
            "Example: {'Foundations': 2800000, 'Individuals': 3200000, 'Government': 1200000, 'Events': 800000}"
        ),
    )
    org_name: Optional[str] = Field(
        None, description="Organization name for report header"
    )
    fiscal_year: Optional[str] = Field(
        None, description="Fiscal year or period (e.g., 'FY2025')"
    )

    def run(self):
        org = self.org_name or "Organization"
        period = self.fiscal_year or "Current Period"
        lines = [f"# Nonprofit Financial Health Analysis: {org} ({period})\n"]

        has_data = False

        # Program Expense Ratio
        if self.program_expenses and self.total_expenses and self.total_expenses > 0:
            ratio = self.program_expenses / self.total_expenses * 100
            benchmark = "✓ Strong (>75%)" if ratio >= 75 else ("⚠️ Monitor (65–75%)" if ratio >= 65 else "⛔ Below benchmark (<65%)")
            lines.append(f"## Program Expense Ratio: {ratio:.1f}%")
            lines.append(f"  {benchmark}")
            lines.append(f"  Program: ${self.program_expenses:,.0f} / Total Expenses: ${self.total_expenses:,.0f}")
            lines.append("  *Benchmark: ≥75% of expenses going to programs (Charity Navigator standard)*\n")
            has_data = True

        # Fundraising Efficiency
        if self.fundraising_expenses and self.total_contributions and self.total_contributions > 0:
            cost_per_dollar = self.fundraising_expenses / self.total_contributions
            benchmark = "✓ Efficient (<$0.20 per $1 raised)" if cost_per_dollar < 0.20 else ("⚠️ Monitor ($0.20–0.35)" if cost_per_dollar < 0.35 else "⛔ High cost (>$0.35 per $1)")
            lines.append(f"## Fundraising Efficiency: ${cost_per_dollar:.2f} per dollar raised")
            lines.append(f"  {benchmark}")
            lines.append(f"  Fundraising Expenses: ${self.fundraising_expenses:,.0f}\n")
            has_data = True

        # Months of Operating Cash
        if self.unrestricted_net_assets and self.total_expenses and self.total_expenses > 0:
            monthly_expenses = self.total_expenses / 12
            months = self.unrestricted_net_assets / monthly_expenses
            benchmark = "✓ Strong (>6mo)" if months >= 6 else ("⚠️ Adequate (3–6mo)" if months >= 3 else "⛔ Vulnerable (<3mo)")
            lines.append(f"## Months of Operating Cash: {months:.1f} months")
            lines.append(f"  {benchmark}")
            lines.append(f"  Unrestricted Net Assets: ${self.unrestricted_net_assets:,.0f}")
            lines.append(f"  Monthly Expenses: ${monthly_expenses:,.0f}\n")
            has_data = True

        # Net Asset Trend
        if self.current_year_net_assets and self.prior_year_net_assets and self.prior_year_net_assets > 0:
            change = self.current_year_net_assets - self.prior_year_net_assets
            pct_change = change / self.prior_year_net_assets * 100
            direction = "↑" if change > 0 else "↓"
            lines.append(f"## Net Asset Trend: {direction} {abs(pct_change):.1f}% year-over-year")
            lines.append(f"  Prior Year: ${self.prior_year_net_assets:,.0f}  →  Current: ${self.current_year_net_assets:,.0f}")
            lines.append(f"  Change: {'+'if change>0 else ''}{change:,.0f}\n")
            has_data = True

        # Revenue Diversification (HHI)
        if self.revenue_sources and sum(self.revenue_sources.values()) > 0:
            total = sum(self.revenue_sources.values())
            shares = [v / total for v in self.revenue_sources.values()]
            hhi = sum(s ** 2 for s in shares) * 10000  # Scale to 0–10,000
            if hhi < 2500:
                diversity = "✓ Diversified (HHI <2,500)"
            elif hhi < 5000:
                diversity = "⚠️ Moderate concentration (HHI 2,500–5,000)"
            else:
                diversity = "⛔ Concentrated revenue risk (HHI >5,000)"
            lines.append(f"## Revenue Diversification Index (HHI): {hhi:.0f}")
            lines.append(f"  {diversity}")
            lines.append("  Revenue by source:")
            for source, amount in sorted(self.revenue_sources.items(), key=lambda x: -x[1]):
                pct = amount / total * 100
                lines.append(f"    {source}: ${amount:,.0f} ({pct:.1f}%)")
            lines.append("")
            has_data = True

        # Summary
        if self.total_revenue and self.total_expenses:
            surplus = self.total_revenue - self.total_expenses
            lines.append(f"## Financial Summary")
            lines.append(f"  Total Revenue: ${self.total_revenue:,.0f}")
            lines.append(f"  Total Expenses: ${self.total_expenses:,.0f}")
            lines.append(f"  Net {'Surplus' if surplus >= 0 else 'Deficit'}: ${'+'if surplus>=0 else ''}{surplus:,.0f}")
            has_data = True

        if not has_data:
            return (
                "No financial data provided. Supply at least one of: total_revenue, "
                "total_expenses, program_expenses, unrestricted_net_assets, or revenue_sources."
            )

        lines.append(
            "\n---\n"
            "**Notes:**\n"
            "  • Benchmarks are general nonprofit sector standards; compare to peer organizations\n"
            "  • Data quality flags: verify figures against signed 990 or audited statements\n"
            "  • Use ChartBuilder to visualize revenue diversification or trend data"
        )
        return "\n".join(lines)


if __name__ == "__main__":
    print("=== Test: LFLA-like financial ratios ===")
    tool = FinancialRatios(
        org_name="Library Foundation of Los Angeles",
        fiscal_year="FY2025",
        total_revenue=10_200_000,
        total_expenses=9_800_000,
        program_expenses=7_840_000,
        management_expenses=980_000,
        fundraising_expenses=980_000,
        total_contributions=8_200_000,
        unrestricted_net_assets=18_000_000,
        current_year_net_assets=65_000_000,
        prior_year_net_assets=61_000_000,
        revenue_sources={
            "Major Donors": 3_200_000,
            "Foundation Grants": 2_800_000,
            "Government": 1_200_000,
            "Corporate": 1_000_000,
            "Events and Other": 1_000_000,
            "Investment": 1_000_000,
        },
    )
    print(tool.run())
