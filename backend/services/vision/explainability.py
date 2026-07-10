"""Explainability adapter contract.

Production deployments may add classifier-specific Grad-CAM or attention maps here.
They must remain secondary explanations and must never be used as the only proof of
where a disease is located. The current package intentionally generates no heatmap
without a compatible trained model and validated layer mapping.
"""


def capability() -> dict:
    return {
        "available": False,
        "method": "not_configured",
        "requires": "validated model-specific explainability adapter",
    }
