# Financial Arithmetic and Evaluation Limits

> This experimental dry-run preview cannot submit or fill orders and has no verified live-money performance record. The examples below explain terminology only; they are not preview results, forecasts, or earning claims.

## Sell-only scope

This preview does **not** buy, open, sell, amend, or cancel event-contract positions. It simulates sell planning for positions already held in the configured account. The inventory and its original cost basis come from outside this project.

## How sell arithmetic works in principle

For filled sell orders:

- **Gross sale proceeds** = contracts filled × sell price.
- **Gross trading profit** = gross sale proceeds − original position cost.
- **Net result** = gross trading profit − exchange fees and other costs.

At the simulator’s default **2¢ target**, arithmetic examples are:

| Filled contracts | Gross sale proceeds |
|---:|---:|
| 1,000 | $20 |
| 10,000 | $200 |
| 100,000 | $2,000 |

These figures are proceeds, not guaranteed profit. For example, 10,000 contracts filled at 2¢ produce $200 in gross proceeds, but the net result could be positive, zero, or negative after the original cost basis and fees are included.

## Why realized results can be worse

- The sell order may never fill or may fill only partially.
- Other traders may have queue priority.
- Fees and fee rounding can change the economics.
- The market can move before or after a fill.
- Unsold contracts retain market and settlement risk.
- Exchange pauses, network failures, API changes, or software defects may interrupt management.
- Capital and exposure can remain tied up while better opportunities pass.

## What meaningful evaluation requires

Track results by cohort and separate:

- gross proceeds, gross profit, and net profit;
- submitted orders from actual fills;
- demo/simulation from production;
- realized from unrealized P&L;
- time in queue and capital duration;
- unsold position value and settlement outcome;
- outages, rejects, retries, and manual interventions.

Use enough independent observations to avoid treating a lucky sequence as a strategy edge. Publish the cost-basis method, fees, sample size, exclusions, losses, and drawdowns—not only winning examples.

## Responsible statement

The preview can help reviewers study disciplined sell-management logic, but it cannot execute that logic. It has **no earning rate, no verified performance record, and no profit claim**. Actual results from any separate order-capable system would depend on entry economics, fees, liquidity, reliability, and execution.
