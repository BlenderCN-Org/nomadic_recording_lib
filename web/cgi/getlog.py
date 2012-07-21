#!/usr/bin/env python


import cgi
import cgitb
cgitb.enable()
import os.path
import gzip
import tarfile
import tempfile
import StringIO

logfiledata = {'wowza': {'root':'/usr/local/WowzaMediaServer/logs/',
                         'filename_fmt':'wowzamediaserver_%s.log',
                         'filenames':['access', 'error', 'stats']},
               'apache':{'root':'/var/log/apache2/',
                         'filename_fmt':'%s.log',
                         'filenames':['access','error']}}

def wrapdochtml(body, head=None):
    if head is None:
        head = ''
    return '<html>\n<head>%s</head>\n<body>\n%s\n</body>\n</html>' % (head, body)

def get_logfiles(app, filetype, wraphtml, getall):
    basepath, basefn = os.path.split(findlogfilename(app, filetype))
    if getall:
        filenames = find_all_logfiles(app, filetype)
        logs = []
        for i, fn in enumerate(filenames):
            fullpath = os.path.join(basepath, fn)
            s = getlogfile(fullpath)
            if wraphtml:
                s = wraploghtml(s, '%s-%s' % (filetype, i))
            logs.append({'filename':fn, 
                         'stats':os.stat(fullpath), 
                         'contents':s})
        return logs, basefn
        outfile = build_archive(logs)
        #outfile = logs
        outfilename = '.'.join([basefn, 'tar.gz'])
        return outfile, outfilename
    filename = findlogfilename(app, filetype)
    s = getlogfile(filename)
    if wraphtml:
        s = wraploghtml(s, filetype)
    return s, basefn
        
def find_all_logfiles(app, filetype):
    filename = findlogfilename(app, filetype)
    basedir, basefn = os.path.split(filename)
    filenames = []
    for fn in os.listdir(basedir):
        if basefn in fn:
            filenames.append(fn)
    filenames.sort()
    filenames.reverse()
    filenames.remove(basefn)
    filenames = [basefn] + filenames
    return filenames

def findlogfilename(app, filetype):
    data = logfiledata[app]
    filename = os.path.join(data['root'], data['filename_fmt'] % filetype)
    return filename

def getlogfile(filename):
    ext = os.path.splitext(filename)[1]
    if ext == '.gz':
        file = gzip.open(filename, 'rb')
    else:
        file = open(filename, 'r')
    s = file.read()
    file.close()
    return s
        
def wraploghtml(logstr, div_id, line_breaks=True):
    if line_breaks:
        logstr = '<br>'.join(logstr.splitlines())
    return '<div id=%s>%s</div>' % (div_id, logstr)

def build_archive(logs):
    fd = tempfile.SpooledTemporaryFile()
    tar = tarfile.open(mode='w:gz', fileobj=fd)
    bufs = []
    for logdata in logs:
        tinf = tarfile.TarInfo(logdata['filename'])
        tinf.mtime = logdata['stat'].st_mtime
        tinf.mode = logdata['stat'].st_mode
        buf = StringIO()
        buf.write(logdata['contents'])
        buf.seek(0)
        bufs.append(buf)
        tinf.size = len(buf.buf)
        tar.addfile(tinf, fileobj=buf)
    tar.close()
    for buf in bufs:
        buf.close()
    fd.seek(0)
    s = fd.read()
    fd.close()
    return s


def parse_to_bool(s):
    return s.lower() in ['true', 'yes']

form = cgi.FieldStorage()
logapp = form.getfirst('app', None)
logfile = form.getfirst('file', None)
wraphtml = parse_to_bool(form.getfirst('wraphtml', 'true'))
getall = parse_to_bool(form.getfirst('getall', 'false'))


content_type = 'text/html'
if getall:
    wraphtml = False
    #content_type = 'application/x-tar-gz'
if not wraphtml:
    content_type = 'text/plain'
    
#logdiv, logfilename = findlogfile(logapp, logfile, wraphtml)
print 'Content-Type: %s' % (content_type)
print

logfileresult, logfilename = get_logfiles(logapp, logfile, wraphtml, getall)
#logfileresult, logfilename = ('blahstuff', 'blahname')

if wraphtml:
    body = '<h1>%s</h1>%s' % (logfilename, logfileresult)
    print wrapdochtml(body)
else:
    #print 'Content-Disposition: attachment; filename=%s' % (logfilename)
    #print
    if getall:
        #print '# %s' % ([ld['filename'] for ld in logfileresult])
        for logdata in logfileresult:
            print logdata['contents']
    else:
        print logfileresult

