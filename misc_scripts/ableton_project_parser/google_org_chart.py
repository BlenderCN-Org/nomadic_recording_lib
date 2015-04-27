import os
import json

from parser import parse_als

def build_json_data(filename):
    root_node = parse_als(filename)
    def build_row(node):
        if node.parent is None:
            parent_id = ''
        else:
            parent_id = node.parent.uid
        return [
            {'v':node.uid, 'f':node.tag}, 
            {'v':parent_id, 'f':parent_id}, 
            #str(node.node.attrib), 
        ]
    d = {
        'cols':[
            {'id':'node_id', 'label':'Name', 'type':'string'}, 
            {'id':'parent_id', 'label':'parent_id', 'type':'string'}, 
            #{'id':'tooltip', 'label':'Tooltip', 'type':'string'},  
        ], 
        'rows':[], 
    }
    for node in root_node.walk():
        d['rows'].append(build_row(node))
    return {'cols':json.dumps(d['cols']), 'rows':json.dumps(d['rows'])}
    
HTML_TEMPLATE = '''
<html>
<head>
<script type="text/javascript" src="https://www.google.com/jsapi"></script>
<script type="text/javascript">
    var data_table = null;
    var column_data = %(cols)s;
    var row_data = %(rows)s;
    google.load("visualization", "1", {packages:["orgchart"]});
    google.setOnLoadCallback(drawChart);
    function drawChart() {
        data_table = new google.visualization.DataTable();
        for (var i=0; i<column_data.length; i++){
            data_table.addColumn(column_data[i]);
            console.log('added column: ', column_data[i]);
        }
        for (var i=0; i<row_data.length; i++){
            data_table.addRow(row_data[i]);
            console.log(i);
        }
        var chart = new google.visualization.OrgChart(document.getElementById('chart_div'));
        chart.draw(data_table, {'allowCollapse':true});
    }
</script>
</head>
<body>
    <div id="chart_div"></div>
</body>
</html>
'''

def build_html(als_filename, html_filename=None):
    if html_filename is None:
        p = os.path.dirname(als_filename)
        fn = '.'.join([os.path.splitext(os.path.basename(als_filename))[0], 'html'])
        html_filename = os.path.join(p, fn)
    json_data = build_json_data(als_filename)
    html_str = HTML_TEMPLATE % json_data
    with open(html_filename, 'w') as f:
        f.write(html_str)
    
    
