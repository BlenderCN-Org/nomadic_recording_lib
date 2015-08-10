#! /usr/bin/env python
import subprocess
import argparse

CHANNEL_MAP = {
    'FL':'front_left', 
    'FR':'front_right', 
    'FC':'front_center', 
    'LFE':'lfe', 
    'SL':'side_left', 
    'SR':'side_right', 
}

CHANNEL_LAYOUTS = {
    '5.1':'5.1[FL][FR][FC][LFE][SL][SR]', 
}

def parse_layout(layout_str):
    channels = {}
    layout_str = '['.join(layout_str.split('[')[1:])
    for s in layout_str.split('['):
        s = s.split(']')[0]
        channels['[%s]' % (s)] = CHANNEL_MAP.get(s)
    return channels
    
def build_cmd(**kwargs):
    infile = kwargs.get('infile')
    layout = kwargs.get('layout')
    layout_str = kwargs.get('layout_str')
    if not layout_str:
        layout_str = CHANNEL_LAYOUTS.get(layout)
    output_prefix = kwargs.get('output_prefix')
    output_ext = kwargs.get('output_ext')
    if output_ext.startswith('.'):
        output_ext = output_ext[1:]
    channels = parse_layout(layout_str)
    maps = []
    for key, chan_name in channels.items():
        outfn = '.'.join([chan_name, output_ext])
        if output_prefix is not None:
            outfn = ''.join([output_prefix, outfn])
        maps.append("-map '%s' '%s'" % (key, outfn))
    cmd_str = "avconv -i '%s' -filter_complex 'channelsplit=channel_layout=%s'" % (
        infile, layout_str)
    cmd_str = ' '.join([cmd_str] + maps)
    return cmd_str
    
def main():
    p = argparse.ArgumentParser()
    p.add_argument('-i', dest='infile')
    p.add_argument('-p', dest='output_prefix')
    p.add_argument('--ext', dest='output_ext', default='wav')
    p.add_argument('--layout', dest='layout', default='5.1')
    p.add_argument('--layout-str', dest='layout_str')
    args, remaining = p.parse_known_args()
    o = vars(args)
    cmd_str = build_cmd(**o)
    print(cmd_str)
    s = subprocess.check_output(cmd_str, shell=True)
    print(s)
    
    
if __name__ == '__main__':
    main()
    
    
