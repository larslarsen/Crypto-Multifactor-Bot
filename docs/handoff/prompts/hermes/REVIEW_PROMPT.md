# Hermes review prompt

Review the current ticket diff as a skeptical staff data/platform engineer. Do not add features. Identify violations of point-in-time semantics, immutability, idempotency, atomicity, deterministic identity, layer boundaries, bounded resource use, and failure policy. Run the ticket's acceptance commands. Provide blocking findings first, with exact file and line references, then non-blocking improvements.
