#! /usr/bin/env python

import os.path
import subprocess
import argparse

def LOG(*args):
    entry = ' '.join([str(arg) for arg in args])
    print entry

def handle_filenames(**kwargs):
    infile = kwargs.get('infile')
    inpath = os.path.dirname(infile)
    infile = os.path.basename(infile)
    outfile = kwargs.get('outfile')
    outext = kwargs.get('outext', 'mp4')
    if outfile is None:
        outfile = '.'.join([os.path.splitext(infile)[0], outext])
        outpath = kwargs.get('outpath')
        if outpath is None:
            outpath = inpath
    else:
        outpath = os.path.dirname(outfile)
        outfile = os.path.basename(outfile)
    kwargs.update({
        'infile':infile,
        'inpath':inpath,
        'infile_full':os.path.join(inpath, infile),
        'outfile':outfile,
        'outpath':outpath,
        'outfile_full':os.path.join(outpath, outfile),
    })
    return kwargs

def build_avconv_str(**kwargs):
    s = 'avconv -i "%(infile_full)s" -vcodec copy -acodec copy %(outfile_full)s'
    return s % (kwargs)

def convert_file(**kwargs):
    kwargs = handle_filenames(**kwargs)
    if os.path.exists(kwargs.get('outfile_full')) and not kwargs.get('overwrite'):
        LOG('%s exists.. skipping' % (kwargs.get('outfile')))
        return
    cmd_str = build_avconv_str(**kwargs)
    cmd_out = subprocess.check_output(cmd_str, shell=True)
    LOG(cmd_out)
    

def convert_dir(**kwargs):
    inpath = kwargs.get('inpath')
    outpath = kwargs.get('outpath')
    outext = kwargs.get('outext', 'mp4')
    if not outpath:
        outpath = inpath
    for fn in os.listdir(inpath):
        try:
            fext = os.path.splitext(fn)[1]
        except:
            fext = ''
        if 'f4v' not in fext:
            continue
        fkwargs = {'infile':os.path.join(inpath, fn), 'outpath':outpath, 'outext':outext}
        LOG('converting: ', fkwargs)
        convert_file(**fkwargs)

def main():
    p = argparse.ArgumentParser()
    for arg in ['infile', 'inpath', 'outfile', 'outpath']:
        p.add_argument('--%s' % (arg), dest=arg)
    p.add_argument('--convert-dir', dest='convert_dir', action='store_true')
    p.add_argument('--overwrite', dest='overwrite', action='store_true')
    args, remaining = p.parse_known_args()
    o = vars(args)
    if o.get('convert_dir'):
        convert_dir(**o)
    else:
        convert_file(**o)

if __name__ == '__main__':
    main()


