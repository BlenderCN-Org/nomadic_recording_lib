
def main(**kwargs):
    conf_fn = kwargs.get('conf_file')
    config = kwargs.get('config')
    if conf_fn:
        config = json.load(conf_fn)
    
