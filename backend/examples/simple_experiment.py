"""
Simple example showing how to use TrackAI for experiment tracking.

This example demonstrates:
- Initializing a run with configuration
- Logging metrics at different steps
- Logging system metrics
- Finishing a run
"""

import trackai
import time
import random

# Initialize a new run
run = trackai.init(
    project="example-project",
    name="simple-experiment",
    group="demo",
    config={
        "learning_rate": 0.001,
        "batch_size": 32,
        "optimizer": "adam",
        "model": {
            "architecture": "resnet50",
            "pretrained": True,
        },
    },
)

print(f"Started run: {run}")

# Simulate training loop
for step in range(10):
    # Simulate some training metrics
    loss = 1.0 - (step * 0.08) + random.uniform(-0.05, 0.05)
    accuracy = 0.5 + (step * 0.04) + random.uniform(-0.02, 0.02)
    lr = 0.001 * (0.95 ** step)

    # Log metrics
    trackai.log(
        {
            "train/loss": loss,
            "train/accuracy": accuracy,
            "train/learning_rate": lr,
        },
        step=step,
    )

    print(f"Step {step}: loss={loss:.4f}, accuracy={accuracy:.4f}")

    # Simulate system metrics every few steps
    if step % 3 == 0:
        trackai.log_system(
            {
                "system/gpu_utilization": random.uniform(0.7, 0.95),
                "system/memory_used_gb": random.uniform(6.0, 8.0),
            }
        )

    time.sleep(0.1)  # Simulate training time

# Log validation metrics
trackai.log(
    {
        "val/loss": 0.25,
        "val/accuracy": 0.92,
        "val/f1_score": 0.91,
    }
)

print("\nTraining complete!")
print(f"Final metrics logged for run: {run.run_name}")

# Finish the run
trackai.finish()
print("Run finished successfully!")
