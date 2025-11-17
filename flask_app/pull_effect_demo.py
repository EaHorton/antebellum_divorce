"""
Demo: Pie Chart with Pull Effect - Multiple Examples

This script demonstrates different pull configurations for pie charts,
similar to the Plotly example you provided.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Example 1: Pull out one slice (like your example)
labels1 = ['Oxygen', 'Hydrogen', 'Carbon_Dioxide', 'Nitrogen']
values1 = [4500, 2500, 1053, 500]
pull1 = [0, 0, 0.2, 0]  # Pull out Carbon_Dioxide

# Example 2: Pull out the largest slice
labels2 = ['Desertion', 'Adultery', 'Cruelty', 'Other']
values2 = [450, 250, 180, 120]
pull2 = [0.2, 0, 0, 0]  # Pull out the largest (Desertion)

# Example 3: Pull out multiple slices
labels3 = ['Category A', 'Category B', 'Category C', 'Category D']
values3 = [300, 200, 150, 100]
pull3 = [0.1, 0.2, 0, 0]  # Pull out two slices with different amounts

# Create subplots with 3 pie charts
fig = make_subplots(
    rows=1, cols=3,
    subplot_titles=('Example 1: Pull One Slice', 
                    'Example 2: Pull Largest', 
                    'Example 3: Pull Multiple'),
    specs=[[{'type': 'pie'}, {'type': 'pie'}, {'type': 'pie'}]]
)

# Add traces
fig.add_trace(
    go.Pie(labels=labels1, values=values1, pull=pull1, name="Example 1"),
    row=1, col=1
)

fig.add_trace(
    go.Pie(labels=labels2, values=values2, pull=pull2, name="Example 2"),
    row=1, col=2
)

fig.add_trace(
    go.Pie(labels=labels3, values=values3, pull=pull3, name="Example 3"),
    row=1, col=3
)

# Update layout
fig.update_traces(textposition='inside', textinfo='percent+label')
fig.update_layout(
    title_text="Pie Chart Pull Effect Examples",
    height=500,
    showlegend=True
)

print("\n=== Pie Chart Pull Effect Demo ===")
print("\nExample 1: Pull parameter = [0, 0, 0.2, 0]")
print("  - Pulls out the 3rd slice (Carbon_Dioxide)")
print("\nExample 2: Pull parameter = [0.2, 0, 0, 0]")
print("  - Pulls out the 1st slice (largest value)")
print("\nExample 3: Pull parameter = [0.1, 0.2, 0, 0]")
print("  - Pulls out two slices with different amounts")
print("\n✨ Opening interactive demo in your browser...")

fig.show()
