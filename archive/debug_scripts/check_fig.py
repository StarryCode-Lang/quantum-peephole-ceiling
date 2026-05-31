from PIL import Image
im = Image.open('figures/final/fig1_phase_transition.png')
print(f'fig1 size: {im.size}, mode: {im.mode}')
im2 = Image.open('figures/final/fig2_fss.png')
print(f'fig2 size: {im2.size}, mode: {im2.mode}')
# 3-panel (our): ~4200x1260, 8-panel (old): ~2400x1600  
print(f'fig1: {im.size[0]}x{im.size[1]}')
print(f'fig2: {im2.size[0]}x{im2.size[1]}')