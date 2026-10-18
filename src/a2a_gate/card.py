"""Agent card for the lab.

The URL is a placeholder the process was configured with. The card is not
signed. This is not a live registration.
"""

from __future__ import annotations

from a2a_gate import __version__


def build_card(base_url: str) -> dict[str, object]:
    root = base_url.rstrip("/")
    return {
        "name": "Nube Austral Back Office",
        "description": (
            "Lab agent for the fictional company Nube Austral. "
            "It proposes back-office actions. Risky effects wait for a second person."
        ),
        "provider": {
            "organization": "Nube Austral (fictional)",
            "url": root,
        },
        "version": __version__,
        "protocolVersion": "0.1-lab",
        "documentationUrl": "",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "stateTransitionHistory": False,
            "humanApprovalGate": True,
        },
        "securitySchemes": {},
        "security": [],
        "defaultInputModes": ["text/plain", "application/json"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {
                "id": "read_record",
                "name": "Read a record",
                "description": "Local read. No downstream effect.",
            },
            {
                "id": "draft_notice",
                "name": "Draft a customer notice",
                "description": "Local draft only. Sending a notice is not implemented.",
            },
            {
                "id": "issue_credit_note",
                "name": "Issue a credit note",
                "description": "Effectful. The ledger amount selects the threshold.",
            },
            {
                "id": "change_supplier_bank",
                "name": "Change a supplier bank account",
                "description": "Effectful. Always waits for a second person.",
            },
        ],
        "supportedInterfaces": [
            {
                "url": root,
                "protocolBinding": "LAB-HTTP",
                "protocolVersion": "0.1-lab",
            }
        ],
        "signatures": [],
        "labNotice": "Unsigned lab card. Placeholder URL. Not a deployment.",
    }
