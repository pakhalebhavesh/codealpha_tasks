import csv
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path
from typing import Dict, List, Optional


def to_currency(val: Decimal) -> str:
    """Formats a Decimal value to standard 2-decimal currency string."""
    return f"${val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}"


@dataclass
class Position:
    """Represents a holding in a single stock asset."""
    symbol: str
    shares: Decimal
    cost_basis_per_share: Decimal = field(default_factory=lambda: Decimal("0.00"))

    @property
    def total_cost(self) -> Decimal:
        return (self.shares * self.cost_basis_per_share).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def current_market_value(self, current_price: Decimal) -> Decimal:
        return (self.shares * current_price).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    def unrealized_pnl(self, current_price: Decimal) -> Decimal:
        return self.current_market_value(current_price) - self.total_cost


class MarketDataProvider:
    """Provides market rates and allows dynamic manual price injection."""

    def __init__(self):
        # Baseline simulation values
        self._price_board: Dict[str, Decimal] = {
            "AAPL": Decimal("180.50"),
            "TSLA": Decimal("245.20"),
            "MSFT": Decimal("425.80"),
            "AMZN": Decimal("178.10"),
            "GOOGL": Decimal("165.40"),
            "NVDA": Decimal("120.30"),
        }

    def get_price(self, symbol: str) -> Optional[Decimal]:
        return self._price_board.get(symbol.upper())

    def update_or_add_price(self, symbol: str, price: Decimal) -> None:
        if price <= Decimal("0"):
            raise ValueError("Price must be strictly positive.")
        self._price_board[symbol.upper()] = price


class PortfolioManager:
    """Encapsulates core business rules, positions, and analytics."""

    def __init__(self, market_data: MarketDataProvider):
        self.market_data = market_data
        self.positions: Dict[str, Position] = {}

    def upsert_position(
        self, symbol: str, shares: Decimal, cost_basis: Optional[Decimal] = None
    ) -> None:
        symbol = symbol.upper().strip()
        if shares <= Decimal("0"):
            raise ValueError("Share count must be greater than 0.")

        current_market = self.market_data.get_price(symbol)
        if cost_basis is None:
            cost_basis = current_market if current_market else Decimal("100.00")

        if symbol in self.positions:
            # Weighted average cost basis calculation
            existing = self.positions[symbol]
            new_shares = existing.shares + shares
            blended_cost = (
                (existing.shares * existing.cost_basis_per_share)
                + (shares * cost_basis)
            ) / new_shares
            self.positions[symbol] = Position(
                symbol=symbol,
                shares=new_shares,
                cost_basis_per_share=blended_cost.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                ),
            )
        else:
            self.positions[symbol] = Position(
                symbol=symbol, shares=shares, cost_basis_per_share=cost_basis
            )

    def calculate_metrics(self) -> Dict:
        """Calculates portfolio value, total PnL, and allocation ratios."""
        summary = {
            "total_cost": Decimal("0.00"),
            "total_value": Decimal("0.00"),
            "items": [],
        }

        for symbol, pos in sorted(self.positions.items()):
            price = self.market_data.get_price(symbol) or pos.cost_basis_per_share
            mkt_val = pos.current_market_value(price)
            pnl = pos.unrealized_pnl(price)

            summary["total_cost"] += pos.total_cost
            summary["total_value"] += mkt_val

            summary["items"].append(
                {
                    "symbol": symbol,
                    "shares": pos.shares,
                    "cost_basis": pos.cost_basis_per_share,
                    "current_price": price,
                    "market_value": mkt_val,
                    "pnl": pnl,
                }
            )

        summary["net_pnl"] = summary["total_value"] - summary["total_cost"]
        summary["pnl_percentage"] = (
            (summary["net_pnl"] / summary["total_cost"] * Decimal("100")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if summary["total_cost"] > Decimal("0")
            else Decimal("0.00")
        )
        return summary

    def export_summary(self, filepath: Path, fmt: str = "txt") -> None:
        """Exports the current portfolio in TXT, CSV, or JSON format."""
        metrics = self.calculate_metrics()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if fmt == "txt":
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("=" * 65 + "\n")
                f.write(f"PORTFOLIO PERFORMANCE REPORT | {now_str}\n")
                f.write("=" * 65 + "\n")
                f.write(
                    f"{'Ticker':<8}{'Shares':<10}{'Avg Cost':<12}{'Price':<12}{'Value':<14}{'Unrealized PnL'}\n"
                )
                f.write("-" * 65 + "\n")

                for item in metrics["items"]:
                    pnl_sign = "+" if item["pnl"] >= Decimal("0") else ""
                    f.write(
                        f"{item['symbol']:<8}"
                        f"{item['shares']:<10.2f}"
                        f"{to_currency(item['cost_basis']):<12}"
                        f"{to_currency(item['current_price']):<12}"
                        f"{to_currency(item['market_value']):<14}"
                        f"{pnl_sign}{to_currency(item['pnl'])}\n"
                    )

                f.write("=" * 65 + "\n")
                f.write(f"Total Invested : {to_currency(metrics['total_cost'])}\n")
                f.write(f"Current Value  : {to_currency(metrics['total_value'])}\n")
                sign = "+" if metrics["net_pnl"] >= Decimal("0") else ""
                f.write(
                    f"Net Return     : {sign}{to_currency(metrics['net_pnl'])} ({sign}{metrics['pnl_percentage']}%)\n"
                )

        elif fmt == "csv":
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["Symbol", "Shares", "AvgCost", "CurrentPrice", "MarketValue", "PnL"]
                )
                for item in metrics["items"]:
                    writer.writerow(
                        [
                            item["symbol"],
                            str(item["shares"]),
                            str(item["cost_basis"]),
                            str(item["current_price"]),
                            str(item["market_value"]),
                            str(item["pnl"]),
                        ]
                    )

        elif fmt == "json":
            payload = {
                "generated_at": now_str,
                "summary": {
                    "total_cost": str(metrics["total_cost"]),
                    "total_value": str(metrics["total_value"]),
                    "net_pnl": str(metrics["net_pnl"]),
                    "pnl_percentage": str(metrics["pnl_percentage"]),
                },
                "positions": [
                    {
                        "symbol": i["symbol"],
                        "shares": str(i["shares"]),
                        "cost_basis": str(i["cost_basis"]),
                        "price": str(i["current_price"]),
                        "value": str(i["market_value"]),
                        "pnl": str(i["pnl"]),
                    }
                    for i in metrics["items"]
                ],
            }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)


class ConsolePortfolioApp:
    """Handles terminal display and user interactions."""

    def __init__(self):
        self.market_data = MarketDataProvider()
        self.portfolio = PortfolioManager(self.market_data)

    def _read_decimal(self, prompt: str) -> Decimal:
        while True:
            raw = input(prompt).strip()
            try:
                val = Decimal(raw)
                if val <= Decimal("0"):
                    print("Value must be strictly positive.")
                    continue
                return val
            except InvalidOperation:
                print("Invalid numeric format. Please enter a valid decimal number.")

    def run(self) -> None:
        while True:
            print("\n" + "=" * 40)
            print(" CODEALPHA PORTFOLIO ANALYTICS ")
            print("=" * 40)
            print("1. Add / Buy Shares")
            print("2. Display Real-time Portfolio")
            print("3. Export Portfolio Summary")
            print("4. Update / Register Ticker Price")
            print("5. Exit")

            choice = input("\nEnter choice (1-5): ").strip()

            if choice == "1":
                ticker = input("Stock symbol (e.g., NVDA, AAPL): ").strip().upper()
                if not ticker.isalnum():
                    print("Invalid ticker symbol.")
                    continue

                shares = self._read_decimal(f"Number of shares for {ticker}: ")
                market_price = self.market_data.get_price(ticker)

                if market_price:
                    print(f"Current detected price: {to_currency(market_price)}")
                    use_market = input("Use current price as purchase basis? (y/n): ").lower() == "y"
                    cost_basis = market_price if use_market else self._read_decimal("Execution price per share: ")
                else:
                    print(f"No existing price feed for {ticker}.")
                    cost_basis = self._read_decimal("Enter purchase price per share: ")
                    self.market_data.update_or_add_price(ticker, cost_basis)

                self.portfolio.upsert_position(ticker, shares, cost_basis)
                print(f"Successfully recorded position: {shares} shares of {ticker}.")

            elif choice == "2":
                if not self.portfolio.positions:
                    print("\nPortfolio is currently empty. Add positions to view analytics.")
                    continue

                metrics = self.portfolio.calculate_metrics()
                print("\n" + "=" * 76)
                print(f"{'Ticker':<8}{'Shares':<10}{'Cost Basis':<14}{'Mkt Price':<14}{'Current Value':<16}{'PnL'}")
                print("-" * 76)

                for item in metrics["items"]:
                    sign = "+" if item["pnl"] >= Decimal("0") else ""
                    print(
                        f"{item['symbol']:<8}"
                        f"{item['shares']:<10.2f}"
                        f"{to_currency(item['cost_basis']):<14}"
                        f"{to_currency(item['current_price']):<14}"
                        f"{to_currency(item['market_value']):<16}"
                        f"{sign}{to_currency(item['pnl'])}"
                    )
                print("=" * 76)
                print(f"Total Invested: {to_currency(metrics['total_cost'])}")
                print(f"Portfolio Val : {to_currency(metrics['total_value'])}")
                total_sign = "+" if metrics["net_pnl"] >= Decimal("0") else ""
                print(f"Unrealized PnL: {total_sign}{to_currency(metrics['net_pnl'])} ({total_sign}{metrics['pnl_percentage']}%)")

            elif choice == "3":
                if not self.portfolio.positions:
                    print("Cannot export an empty portfolio.")
                    continue

                print("\nSupported formats: 1. Plain Text (.txt) | 2. CSV (.csv) | 3. JSON (.json)")
                fmt_choice = input("Select format (1-3): ").strip()
                fmt_map = {"1": ("txt", "portfolio.txt"), "2": ("csv", "portfolio.csv"), "3": ("json", "portfolio.json")}

                if fmt_choice not in fmt_map:
                    print("Invalid selection.")
                    continue

                fmt, filename = fmt_map[fmt_choice]
                target_path = Path.cwd() / filename
                self.portfolio.export_summary(target_path, fmt=fmt)
                print(f"Report exported successfully to: {target_path}")

            elif choice == "4":
                ticker = input("Stock symbol to update: ").strip().upper()
                new_price = self._read_decimal(f"Enter new price for {ticker}: ")
                self.market_data.update_or_add_price(ticker, new_price)
                print(f"Updated price board: {ticker} -> {to_currency(new_price)}")

            elif choice == "5":
                print("Terminating tracker. Goodbye!")
                break
            else:
                print("Invalid command. Choose an option between 1 and 5.")


if __name__ == "__main__":
    app = ConsolePortfolioApp()
    app.run()