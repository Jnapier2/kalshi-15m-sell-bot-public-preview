# LinkedIn Draft — Not Approved for Posting

I’m documenting an **experimental advanced dry-run preview** of a Kalshi 15m sell-management project. It is a private learning artifact, not a public release or production trading product.

The retained Python engine demonstrates authenticated REST and WebSocket reads, position/order/fill reconciliation, fee-aware planning, queue monitoring, state persistence, and operational diagnostics.

For review, I made this copy intentionally non-order-capable. `PUBLIC_PREVIEW_ONLY` and `DRY_RUN` are fixed in source, live CLI paths return a migration message, and every mutating request is rejected again at the final pre-signing boundary. No environment value, acknowledgment, or direct engine invocation enables writes.

This preview cannot place or fill orders and has no verified live-money performance record. Any simulated price or quantity is planning output, not a profit or return claim.

The useful story is the review process: finding unsafe assumptions, narrowing scope, adding regression tests, and choosing a fail-closed preview instead of implying production readiness.

#Python #FinTech #Automation #VibeCoding #CyberSecurity #SoftwareEngineering #PredictionMarkets
