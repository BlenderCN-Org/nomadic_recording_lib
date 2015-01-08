import datetime
import plotly.plotly as py
import plotly.tools as tls
from plotly.graph_objs import *

import net_stats

stream_ids = tls.get_credentials_file()['stream_ids']

traces = {
    'tx':Scatter(x=[], y=[], name='tx', stream=dict(token=stream_ids[0])), 
    'rx':Scatter(x=[], y=[], name='rx', stream=dict(token=stream_ids[1])), 
}
data = {
    'tx':Data([traces['tx']]), 
    'rx':Data([traces['rx']]), 
}
data = Data([traces['tx'], traces['rx']])
figure = Figure(data=data, layout=Layout())
py.plot(figure)

streams = {
    'tx':py.Stream(stream_ids[0]), 
    'rx':py.Stream(stream_ids[1]), 
}
for s in streams.values():
    s.open()

def on_net_stat_update(**kwargs):
    dt = datetime.datetime.fromtimestamp(kwargs.get('timestamp'))
    for key in ['tx', 'rx']:
        s = streams[key]
        val = kwargs['data']['data']['current_%s' % (key)]
        print dt, key, val
        #s.open()
        s.write(dict(x=str(dt), y=val))
        #s.close()
    
def main(**kwargs):
    kwargs.setdefault('output_type', 'callback')
    kwargs.setdefault('output_callback', on_net_stat_update)
    net_stats.main(**kwargs)
    
if __name__ == '__main__':
    main()
