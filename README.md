# EARSHOT — a room-aware disclosure gateway for Alexa+

**Alexa answers the person, but it speaks to the room.**

Every other AI whispers to a private screen. An Echo is a loudspeaker in a shared
room. EARSHOT is a self-hosted MCP server (spec 2025-11-25+, Streamable HTTP) that
sits in front of your calendar, bank, messages and health tools and grades every
disclosure by *who's listening* — FULL / ABSTRACT / EXISTENCE / SILENT — through a
deterministic rules engine with no AI in the hot path.

Because Alexa writes its own sentences from tool data, privacy is enforced *before*
the model ever sees the data. Alexa can't leak what it was never told.

Built for the **Build, Ship, Shape: Amazon Developer Hackathon** (Alexa+ track).

## Status

🚧 Sprint in progress — submission by Oct 24, 00:30 IST. See `MASTER_PLAN.md`.
