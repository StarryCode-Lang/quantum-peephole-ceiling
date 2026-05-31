import os
os.chdir("D:/Desktop/Q-research")
from PIL import Image
for f in ['figures/final/fig3_density_sweep.png', 'figures/final/fig4_algorithm_comparison.png']:
    im = Image.open(f)
    print(f'{f}: {im.size}')
for f in ['figures/fig5_landscape.png']:
    im = Image.open(f)
    print(f'{f}: {im.size}')