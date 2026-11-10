#!/usr/bin/env python3
"""Create a silent MP4 and GIF from the rendered, labelled QML preview states."""
from pathlib import Path
import subprocess

project=Path(__file__).resolve().parents[1]
assets=project/'assets'
command=['ffmpeg','-hide_banner','-loglevel','error','-y']
for name in ('battery-care.png','custom-limits.png','conservation.png'):
    command += ['-loop','1','-t','3.5','-i',str(assets/'screenshots'/name)]
filters=[]
for index in range(3):
    filters.append(f'[{index}:v]fps=30,format=yuv420p,pad=1120:800:0:0:black,setsar=1,setpts=PTS-STARTPTS[v{index}]')
filters += ['[v0][v1]xfade=transition=fade:duration=0.35:offset=3.15[x]',
            '[x][v2]xfade=transition=fade:duration=0.35:offset=6.3[v]']
video=assets/'omacharge-demo.mp4'
command += ['-filter_complex',';'.join(filters),'-map','[v]','-c:v','libx264','-crf','20','-preset','medium','-pix_fmt','yuv420p','-movflags','+faststart','-an',str(video)]
subprocess.run(command,check=True)
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(video),'-filter_complex',
                'fps=10,scale=840:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
                '-loop','0',str(assets/'omacharge-demo.gif')],check=True)
print('Created',video,'and the matching GIF.')
