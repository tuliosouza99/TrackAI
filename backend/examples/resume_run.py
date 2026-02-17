"""
Example demonstrating run resumption.

Shows how to resume an existing run to continue logging metrics.
"""

import trackai

# First, create a run
print("=== Creating initial run ===")
run1 = trackai.init(
    project="example-project",
    name="resumable-run",
    config={"initial_lr": 0.01},
)

trackai.log({"loss": 1.0, "step": 0}, step=0)
trackai.log({"loss": 0.8, "step": 1}, step=1)
print("Logged 2 steps")
trackai.finish()

# Now resume the same run
print("\n=== Resuming the run ===")
run2 = trackai.init(
    project="example-project",
    name="resumable-run",
    resume="allow",  # or "must" to require existing run
)

trackai.log({"loss": 0.6, "step": 2}, step=2)
trackai.log({"loss": 0.4, "step": 3}, step=3)
print("Logged 2 more steps")
trackai.finish()

print("\nRun resumed successfully!")
print(f"All metrics are now part of run: {run2.run_name}")
