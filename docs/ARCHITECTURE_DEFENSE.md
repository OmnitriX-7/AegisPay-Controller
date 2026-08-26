# Razorpay Technical Panel Defense Guide
## FAQ & Architectural Defense for AegisPay-Controller

---

### Q1: Why didn't you just use an LLM with LangChain / prompt engineering to do the reconciliation directly?
**Defense**:
> *"In fintech, LLMs cannot be trusted with sub-cent arithmetic, double-entry invariance, or cumulative balance reconciliations because LLMs are non-deterministic, probabilistic token predictors. If an LLM is off by ₹0.50 on 10,000 transactions, that creates a ₹5,000 un-auditable hole in the general ledger.
> In AegisPay-Controller, we strictly use a **Neuro-Symbolic Dual-Loop Architecture**: the **Symbolic Engine** handles all mathematical verification, double-entry bookkeeping ($Debits \equiv Credits$), and fee schedule checks deterministically ($O(1)$ hash maps). The **LLM Agent Loop** is only invoked for semantic fuzzy disambiguation of dirty bank narrations, root-cause diagnosis of un-reconciled items, and natural-language CFO queries."*

---

### Q2: How does your system handle many-to-one batch settlements (e.g. 50 orders in 1 bank deposit)?
**Defense**:
> *"Real payment gateways like Razorpay settle merchant payouts in aggregated batches (`setl_batch_xxx`). In Pass 2 of our pipeline, our **Batch Settlement Decomposer** groups constituent orders by their batch ID, computes the aggregated Gross, contractual MDR fees, statutory 18% GST, and Section 194-O TDS deductions, and matches them against the single credited Bank UTR. The symbolic verifier checks that $\text{Bank Credit} == \sum \text{Net Orders}$ before sealing the match with an immutable SHA-256 proof hash."*

---

### Q3: What happens when an interchange fee or MDR rate is overcharged?
**Defense**:
> *"Our **Symbolic Fee Validator** checks each gateway event against the contractual rate card (e.g., 0% for UPI, 0.9% for RuPay Debit, 1.8% for Domestic Credit, 2.8% for International Amex). If the gateway billed 2.8% on a domestic card, the invariant fails. The item is passed to the **Honest Exception Classifier**, which generates an `MDR_RATE_DISCREPANCY` exception, computes the exact overcharge delta, drafts a dispute ticket, and provides a proposed journal entry (`Debit: Razorpay Fee Disputes Recoverable`, `Credit: Processing Expense`)."*

---

### Q4: How does your forward cash forecaster model settlement clearing float?
**Defense**:
> *"Our forecaster runs 500 Monte Carlo trajectory simulations over a 14-day horizon. It models dynamic payment inflow distributions, operational daily burn, a 5% rolling reserve buffer for chargebacks, and crucial banking settlement lags (e.g. $T+1$ for UPI, $T+2$ for credit cards, and weekend banking holidays where settlement multipliers drop to 0.20 and rebound on Monday). It outputs the 95% confidence interval bounds and calculates cumulative 'Cash-at-Risk'."*

---

### Q5: How did you benchmark throughput and verify zero numerical drift?
**Defense**:
> *"We built an automated enterprise benchmark runner (`benchmarks/run_benchmark.py`) that tests batches of 50, 200, 1,000, and 5,000 records. At 5,000 records (nearly 9,000 raw multi-source lines), the reconciliation completes in 1.27 seconds (~6,938 rec/sec) with strictly ₹0.0000 precision drift across all scales."*
