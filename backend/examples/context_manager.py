"""
Example using TrackAI with context manager for automatic cleanup.

This demonstrates the recommended pattern using 'with' statement,
which automatically finishes the run when the context exits.
"""

import trackai
import random

# Use context manager - automatically finishes the run
with trackai.init(
    project="example-project",
    name="context-manager-demo",
    config={"epochs": 5, "batch_size": 16},
) as run:
    print(f"Started run: {run}")

    for epoch in range(5):
        loss = 1.0 - (epoch * 0.15) + random.uniform(-0.05, 0.05)
        acc = 0.6 + (epoch * 0.08) + random.uniform(-0.02, 0.02)

        trackai.log(
            {
                "epoch": epoch,
                "loss": loss,
                "accuracy": acc,
            },
            step=epoch,
        )

        print(f"Epoch {epoch}: loss={loss:.4f}, acc={acc:.4f}")

    print("\nRun will be automatically finished!")
# Run is automatically finished here, even if an exception occurs
print("Context exited - run finished!")
