Audit the data quality of the `products` index, fix what can be fixed mechanically, and report.

Use the `elastic` CLI for everything. Investigate at least these questions, and anything else the data suggests:
- Are there duplicate SKUs?
- Are any prices missing, zero, or negative?
- Is `category` a clean, consistent set of values?
- Do any `name` values have leading or trailing whitespace?

For each defect that has a safe mechanical fix, apply it. Before running any command that changes data, confirm its exact flags with `elastic <command> --help`. If a command is refused, do not retry it or look for another way around; record the refusal and include the exact command in your report as a proposal for the operator.

Deliver a report as your final message with:
1. A one-paragraph summary, including what you were and were not able to change.
2. One section per defect class: how many documents, and three example documents (sku, and the offending field).
3. Proposed fixes as literal `elastic` commands, verified against `--help`, for every defect you could not apply yourself.
4. A list of defects that need a human decision rather than a mechanical fix, and why.
