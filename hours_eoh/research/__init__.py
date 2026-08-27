"""
research/ — Experimental modules. NOT stable API.

Callers importing from hours_eoh.research.* are in experimental territory.
Functions here are not wired into dashboard or simulation and may change
without notice.

Current modules:
  investment  — rank_investment_candidates, optimal_investment
  writedown   — ecological write-down modeling (eco-collapse-1, future work)
  exchange    — exchange ACCOUNTING: CollectiveFrame, double-entry Ledger /
                FederationBook, the parity floor, and the exact N=1 anchor.
                Distinct from `coasean`, which asks the economics question
                (how many collectives, at what rates); this one asks whether
                the entries add up whatever the rate is.
"""
