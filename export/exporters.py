import os

def export_chart_and_insights(fig, stats: dict, filepath: str):
    """
    Export the chart as a .png and the statistics as a .txt file.

    Args:
        fig: Matplotlib figure object.
        stats: Dictionary containing key statistics.
        filepath: Target filepath WITHOUT extension.
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(filepath)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        # Export the figure
        fig.savefig(filepath + ".png", bbox_inches="tight", dpi=300, facecolor=fig.get_facecolor())

        # Export the insights
        with open(filepath + ".txt", "w", encoding="utf-8") as f:
            f.write("Key Statistics:\n\n")
            for key, value in stats.items():
                f.write(f"{key}: {value}\n")

    except Exception as e:
        raise RuntimeError(f"Export failed: {str(e)}")
