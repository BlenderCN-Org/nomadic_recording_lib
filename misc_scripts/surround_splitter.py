#! /usr/bin/env python
import os
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
    
def compress_output(**kwargs):
    infiles = kwargs.get('infiles')
    output_fmt = kwargs.get('output_format')
    if output_fmt == 'same':
        return
    elif output_fmt == 'mp3':
        out_ext = 'mp3'
        codec_str = '-ab %(output_bitrate)s' % kwargs
    elif output_fmt == 'aac':
        out_ext = 'm4a'
        codec_str = '-strict experimental -acodec aac'
    for infile in infiles:
        outfn = '.'.join([os.path.splitext(infile)[0], out_ext])
        cmd_str = ' '.join(['avconv -i', infile, codec_str, outfn])
        cmd_str = "avconv -i '%s' %s '%s'" % (infile, codec_str, outfn)
        print(cmd_str)
        result = False
        try:
            s = subprocess.check_output(cmd_str, shell=True)
            print(s)
            result = True
        except subprocess.CalledProcessError as e:
            print e.output
            raise
        if result:
            os.remove(infile)
        
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
    outfiles = []
    for key, chan_name in channels.items():
        outfn = '.'.join([chan_name, output_ext])
        if output_prefix is not None:
            outfn = ''.join([output_prefix, outfn])
        outfiles.append(outfn)
        maps.append("-map '%s' '%s'" % (key, outfn))
    cmd_str = "avconv -i '%s' -filter_complex 'channelsplit=channel_layout=%s'" % (
        infile, layout_str)
    cmd_str = ' '.join([cmd_str] + maps)
    return cmd_str, outfiles
    
def main():
    p = argparse.ArgumentParser()
    p.add_argument('-i', dest='infile')
    p.add_argument('-p', dest='output_prefix')
    p.add_argument('--ext', dest='output_ext', default='wav')
    p.add_argument('--layout', dest='layout', default='5.1')
    p.add_argument('--layout-str', dest='layout_str')
    p.add_argument('--output-fmt', dest='output_format', 
                   choices=['same', 'mp3', 'aac'], default='same')
    p.add_argument('--output-bitrate', dest='output_bitrate', default='320k')
    args, remaining = p.parse_known_args()
    o = vars(args)
    cmd_str, outfiles = build_cmd(**o)
    print(cmd_str)
    outfiles_exist = [os.path.exists(fn) for fn in outfiles]
    if False not in outfiles_exist:
        resp = raw_input('All output files exist. Exit? [Y/n] :')
        if 'n' not in resp.lower():
            return
    else:
        s = subprocess.check_output(cmd_str, shell=True)
        print(s)
    ckwargs = {'infiles':outfiles}
    ckwargs.update(o)
    compress_output(**ckwargs)
    
    
if __name__ == '__main__':
    main()
    
    
