import requests
import pandas as pd

r = requests.get('https://opendata.arcgis.com/datasets/48667a23f3b7468d8cd91afce7a6d047_0.geojson')
jsonobj = r.json()

dictlist = [i['properties'] for i in jsonobj['features']]    

df = pd.DataFrame(dictlist)

print(df.columns)