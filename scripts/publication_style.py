"""
Publication-quality figure style module for Nature/Science/PRL standards.

Provides unified rcParams, colorblind-safe palettes, figure templates,
and statistical annotation helpers.
"""

import os
from typing import List, Tuple, Union

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure


# =============================================================================
# 1. Unified Academic Plotting rcParams Configuration
# =============================================================================

PUBLICATION_RCPARAMS = {
    'font.family': 'serif',
    'font.serif': ['Computer Modern Roman', 'Times New Roman', 'DejaVu Serif'],
    'mathtext.fontset': 'cm',
    'font.size': 9,  # Nature standard: 7-9pt
    'axes.labelsize': 10,
    'axes.titlesize': 10,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'figure.titlesize': 11,
    'lines.linewidth': 1.0,
    'lines.markersize': 4,
    'axes.linewidth': 0.8,
    'xtick.major.width': 0.8,
    'ytick.major.width': 0.8,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.top': True,
    'ytick.right': True,
    'axes.spines.top': True,
    'axes.spines.right': True,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.05,
}


def apply_publication_style():
    """Apply Nature/PRL-standard matplotlib style."""
    plt.rcParams.update(PUBLICATION_RCPARAMS)


# =============================================================================
# 2. Colorblind-Friendly Color Schemes
# =============================================================================

# Wong (2011) Nature Methods colorblind-safe palette
COLORBLIND_PALETTE = {
    'blue': '#0072B2',
    'orange': '#E69F00', 
    'green': '#009E73',
    'pink': '#CC79A7',
    'sky_blue': '#56B4E9',
    'yellow': '#F0E442',
    'red': '#D55E00',
    'black': '#000000',
}

# Sequential palette for system sizes (colorblind-safe)
SEQUENTIAL_PALETTE = [
    '#0072B2', '#56B4E9', '#009E73', '#E69F00', 
    '#D55E00', '#CC79A7', '#F0E442', '#000000'
]


def get_colorblind_colors(n: int) -> List[str]:
    """
    Return n colorblind-safe colors.
    
    Args:
        n: Number of colors needed.
        
    Returns:
        List of hex color strings.
    """
    if n <= len(SEQUENTIAL_PALETTE):
        return SEQUENTIAL_PALETTE[:n]
    # Cycle through palette if more colors are requested
    return [SEQUENTIAL_PALETTE[i % len(SEQUENTIAL_PALETTE)] for i in range(n)]


# =============================================================================
# 3. Journal Standard Figure Templates
# =============================================================================

def create_figure(n_panels: int, layout: str = 'horizontal', 
                  single_column: bool = False) -> Tuple[Figure, List[Axes]]:
    """
    Create publication-ready figure with standard dimensions.
    
    Args:
        n_panels: Number of subplots.
        layout: 'horizontal', 'vertical', or 'grid'.
        single_column: True for 89mm width (Nature single column), 
                       False for 183mm width (Nature double column).
                       
    Returns:
        Tuple of (Figure, List of Axes).
    """
    # Nature dimensions: 1 inch = 25.4 mm
    width = 89.0 / 25.4 if single_column else 183.0 / 25.4
    
    if layout == 'horizontal':
        fig, axes = plt.subplots(1, n_panels, figsize=(width, width / n_panels * 0.75))
    elif layout == 'vertical':
        fig, axes = plt.subplots(n_panels, 1, figsize=(width * 0.6, width * 0.8))
    elif layout == 'grid':
        cols = int(np.ceil(np.sqrt(n_panels)))
        rows = int(np.ceil(n_panels / cols))
        fig, axes = plt.subplots(rows, cols, figsize=(width, width * (rows / cols) * 0.75))
    else:
        raise ValueError("layout must be 'horizontal', 'vertical', or 'grid'")
        
    # Ensure axes is always a flat list
    if n_panels == 1:
        axes_list = [axes]
    else:
        axes_list = np.array(axes).flatten().tolist()
        
    # Remove empty axes if grid layout creates more panels than n_panels
    if len(axes_list) > n_panels:
        for i in range(n_panels, len(axes_list)):
            fig.delaxes(axes_list[i])
        axes_list = axes_list[:n_panels]
        
    fig.tight_layout()
    return fig, axes_list


def add_panel_label(ax: Axes, label: str, position: str = 'top_left'):
    """
    Add (a), (b), (c) panel label in journal style.
    
    Args:
        ax: Matplotlib Axes object.
        label: Panel identifier (e.g., 'a', 'b').
        position: 'top_left' or 'top_right'.
    """
    label_text = f"({label})" if len(label) == 1 else label
    
    if position == 'top_left':
        ax.text(0.02, 0.98, label_text, transform=ax.transAxes,
                fontsize=10, fontweight='bold', va='top', ha='left',
                fontfamily='sans-serif')
    elif position == 'top_right':
        ax.text(0.98, 0.98, label_text, transform=ax.transAxes,
                fontsize=10, fontweight='bold', va='top', ha='right',
                fontfamily='sans-serif')
    else:
        raise ValueError("position must be 'top_left' or 'top_right'")


def save_publication_figure(fig: Figure, base_path: str, formats: List[str] = ['png', 'pdf', 'svg']):
    """
    Save figure in all publication formats with proper settings.
    
    Args:
        fig: Matplotlib Figure object.
        base_path: File path without extension (e.g., 'figures/fig1').
        formats: List of file formats to save.
    """
    dir_name = os.path.dirname(base_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
        
    for fmt in formats:
        filepath = f"{base_path}.{fmt}"
        dpi = 300 if fmt == 'png' else None
        fig.savefig(filepath, format=fmt, dpi=dpi, bbox_inches='tight', pad_inches=0.05)


# =============================================================================
# 4. Formatted Statistical Annotations
# =============================================================================

def format_p_value(p: float) -> str:
    """
    Format p-value in journal style: p < 0.001, p = 0.023, etc.
    
    Args:
        p: P-value float.
        
    Returns:
        Formatted string (supports mathtext).
    """
    if p < 0.001:
        return r"$p < 0.001$"
    else:
        return f"$p = {p:.3f}$"


def format_ci(value: float, ci_lower: float, ci_upper: float, decimals: int = 2) -> str:
    """
    Format confidence interval: 0.297 (95% CI: 0.251–0.343)
    
    Args:
        value: Point estimate.
        ci_lower: Lower bound of confidence interval.
        ci_upper: Upper bound of confidence interval.
        decimals: Number of decimal places.
        
    Returns:
        Formatted string.
    """
    return f"{value:.{decimals}f} (95% CI: {ci_lower:.{decimals}f}\u2013{ci_upper:.{decimals}f})"


def add_significance_marker(ax: Axes, x1: float, x2: float, y: float, p_value: float, text_height: float = 0.02):
    """
    Add significance bracket with asterisks (* p<0.05, ** p<0.01, *** p<0.001).
    
    Args:
        ax: Matplotlib Axes object.
        x1: X-coordinate of the first group.
        x2: X-coordinate of the second group.
        y: Y-coordinate for the base of the bracket.
        p_value: P-value to determine significance.
        text_height: Height of the bracket relative to the y-axis range.
    """
    if p_value < 0.001:
        sig = '***'
    elif p_value < 0.01:
        sig = '**'
    elif p_value < 0.05:
        sig = '*'
    else:
        sig = 'ns'
        
    # Convert text_height from axes fraction to data coordinates
    ymin, ymax = ax.get_ylim()
    h = text_height * (ymax - ymin)
    y_bar = y + h
    
    # Draw bracket
    ax.plot([x1, x1, x2, x2], [y, y_bar, y_bar, y], lw=0.8, color='black')
    
    # Add significance text
    ax.text((x1 + x2) / 2, y_bar + h * 0.1, sig, ha='center', va='bottom', 
            color='black', fontsize=9, fontfamily='sans-serif')
