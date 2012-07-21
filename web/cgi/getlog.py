#!/usr/bin/env python


import cgi
import cgitb
cgitb.enable()
import os.path
import datetime
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

#def get_logfiles(app, filetype, wraphtml, getall):
def get_logfiles(**kwargs):
    app = kwargs.get('app')
    filetype = kwargs.get('file')
    wraphtml = kwargs.get('wraphtml')
    getall = kwargs.get('getall')
    datestart = kwargs.get('datestart')
    dateend = kwargs.get('dateend')
    basepath, basefn = os.path.split(findlogfilename(app, filetype))
    if getall:
        filenames, fn_by_dt = find_all_logfiles(**kwargs)
        if dateend is not None:
            filenames = []
            for dt in reversed(sorted(fn_by_dt.keys())):
                if dt.date < dateend.date:
                    break
                if dt.date >= datestart.date:
                    continue
                filenames.append(fn_by_dt[dt])
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
        
#def find_all_logfiles(app, filetype):
def find_all_logfiles(**kwargs):
    app = kwargs.get('app')
    filetype = kwargs.get('file')
    filename = findlogfilename(app, filetype)
    basedir, basefn = os.path.split(filename)
    filenames = []
    fn_by_dt = {}
    for fn in os.listdir(basedir):
        if basefn not in fn:
            continue
        filenames.append(fn)
        ts = os.stat(os.path.join(basedir, fn)).st_ctime
        dt = datetime.datetime.fromtimestamp(ts)
        fn_by_dt[dt] = fn
    filenames.sort()
    filenames.reverse()
    filenames.remove(basefn)
    filenames = [basefn] + filenames
    return filenames, fn_by_dt

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
    if type(s) == bool:
        return s
    return s.lower() in ['true', 'yes']

form = cgi.FieldStorage()
formdefaults = dict(app=None, file=None, wraphtml=True, getall=False, 
                    datestart=None, dateend=None)
formdata = {}
for key, default in formdefaults.iteritems():
    val = form.getfirst(key, default)
    if type(default) == bool:
        val = parse_to_bool(val)
    formdata[key] = val

#logapp = form.getfirst('app', None)
#logfile = form.getfirst('file', None)
#wraphtml = parse_to_bool(form.getfirst('wraphtml', 'true'))
#getall = parse_to_bool(form.getfirst('getall', 'false'))
def parse_datetime(s):
    fmt_str = '%Y%m%d'
    return datetime.datetime.strptime(s, fmt_str)
    
for key in ['datestart', 'dateend']:
    if formdata[key] is not None:
        formdata[key] = parse_datetime(formdata[key])
        formdata['getall'] = True
if formdata['datestart'] is None:
    formdata['datestart'] = datetime.datetime.now()

content_type = 'text/html'
if formdata['getall']:
    pass
    #formdata['wraphtml'] = False
    #content_type = 'application/x-tar-gz'
if not formdata['wraphtml']:
    content_type = 'text/plain'
    
#logdiv, logfilename = findlogfile(logapp, logfile, wraphtml)
print 'Content-Type: %s' % (content_type)
print

logfileresult, logfilename = get_logfiles(**formdata)
#logfileresult, logfilename = ('blahstuff', 'blahname')

if formdata['wraphtml']:
    body = '<h1>%s</h1>%s' % (logfilename, logfileresult)
    print wrapdochtml(body)
else:
    #print 'Content-Disposition: attachment; filename=%s' % (logfilename)
    #print
    if formdata['getall']:
        #print '# %s' % ([ld['filename'] for ld in logfileresult])
        for logdata in logfileresult:
            print logdata['contents']
    else:
        print logfileresult

