# Information-Backed Dollar (IBD)

Hard-mint rule coupling monetary expansion to verified information gain. Minting occurs only when total justification increases.

## Core objects
- **InfoArtifact**: verifiable structure that increases order/quality of life (math proof, protocol, model, infra upgrade, safety system).
  - `cid` (IPFS content ID)
  - `type`
  - `impact_metrics` (throughput, safety, access, CO2, etc.)
  - `verification_proofs` (tests, audits, peer review)
  - `adoption_evidence` (usage data; optional but inputs J)
- **JustificationScore (J)**: scalar per artifact and in aggregate; measures proven extra order.
  - Per artifact: `J_i = w_i^T * normalize([impact_metrics_i, verification_proofs_i, adoption_i])` with weights fixed by policy and subject to bounds.[1]
  - System total at time t: `J_t = Σ_i J_i` over all registered artifacts with active verification.
- **IBD**: token labelled “dollar”, supply bounded by justified information. Minting is strictly a function of ΔJ.

[1] Weights must be published and invariant within an epoch; normalization functions are deterministic and auditable.

## Mint rule (printing justified by information)
- Define `ΔJ_t = J_t − J_{t−1}`.
- Policy constant `k` maps justification units to currency.
- Minting: `New_IBD_t = max(0, k * ΔJ_t)`.
- If `ΔJ_t < 0`, optionally burn `|k * ΔJ_t|` or set mint to zero; no positive issuance is allowed when justification declines.
- No discretionary inflation targets; issuance is mechanically tied to verified structural gains.

## Fiat alignment
- Legacy fiat → IBD conversion band depends on growth of J.
  - If `ΔJ_t > 0`, a governed band allows fiat to enter as IBD backed by the new justification.
  - If `ΔJ_t ≤ 0`, conversions are frozen; any additional fiat printing becomes visibly unjustified.
- Quality factor: `q_t = J_t / J_0`. Face value remains 1, but effective “realness” scales with cumulative justification.

## Minimum pipeline
1. Register artifact: ingest `InfoArtifact(cid, type, impact_metrics, verification_proofs, adoption_evidence)`.
2. Verify: run audits/tests/peer review; recompute `J_i`; update `J_t`.
3. Compute `ΔJ_t`; apply `New_IBD_t = max(0, k * ΔJ_t)`; optionally burn on negative deltas.
4. Distribute newly minted IBD per policy (builders, verification pool, public treasury).

## Governance and safety
- k, weights, normalization, and burn policy are on-chain and versioned; changes require explicit governance with timelocks.
- Verification proofs must be reproducible; failed or stale proofs zero the associated `J_i` until renewed.
- Anti-gaming: cap per-artifact `J_i`, require independent auditors, and enforce decay on unverifiable adoption metrics.
- Auditable ledger: every mint/burn event includes `(t, ΔJ_t, J_t, k, New_IBD_t, artifacts_delta)` for external verification.
