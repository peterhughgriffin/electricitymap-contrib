#!/usr/bin/env python3

"""Parser for the electricity grid of Chile"""

import arrow
import pandas as pd
import logging
import requests
from collections import defaultdict
from operator import itemgetter

API_BASE_URL = "https://sipub.coordinador.cl/api/v1/recursos/generacion_centrales_tecnologia_horario?"

TYPE_MAPPING = {'hidraulica': 'hydro',
                'termica': 'unknown',
                'eolica': 'wind',
                'solar': 'solar',
                'geotermica': 'geothermal'}


def timestamp_creator(date, hour):
    """Takes a string and int and returns a datetime object"""

    arr_date = arrow.get(date, "YYYY-MM-DD")

    hour -= 1
    dt = pd.to_datetime(date, format='%Y-%m-%d').tz_localize('Chile/Continental')
    dt = dt + pd.DateOffset(hours=hour)
    dt = dt.tz_convert('UTC')

    return dt


def data_processor(raw_data):
    """Takes raw json data and groups by datetime while mapping generation to type.
    Returns a list of dictionaries.
    """

    clean_datapoints = []
    for datapoint in raw_data:
        clean_datapoint = {}
        date, hour = datapoint['fecha'], datapoint['hora']
        clean_datapoint['datetime'] = timestamp_creator(date, hour)

        gen_type_es = datapoint['tipo_central']
        mapped_gen_type = TYPE_MAPPING[gen_type_es]
        value_mw = float(datapoint['generacion_sum'])

        clean_datapoint[mapped_gen_type] = value_mw

        clean_datapoints.append(clean_datapoint)

    combined = defaultdict(dict)
    for elem in clean_datapoints:
        combined[elem['datetime']].update(elem)

    ordered_data = sorted(combined.values(), key=itemgetter("datetime"))

    return ordered_data


def fetch_production(zone_key='CL', session=None, target_datetime=None, logger=logging.getLogger(__name__)):
    """Requests the last known production mix (in MW) of a given zone
    Arguments:
    zone_key (optional) -- used in case a parser is able to fetch multiple zones
    session (optional) -- request session passed in order to re-use an existing session
    target_datetime (optional) -- used if parser can fetch data for a specific day, a string in the form YYYYMMDD
    logger (optional) -- handles logging when parser is run
    Return:
    A list of dictionaries in the form:
    {
      'zoneKey': 'FR',
      'datetime': '2017-01-01T00:00:00Z',
      'production': {
          'biomass': 0.0,
          'coal': 0.0,
          'gas': 0.0,
          'hydro': 0.0,
          'nuclear': null,
          'oil': 0.0,
          'solar': 0.0,
          'wind': 0.0,
          'geothermal': 0.0,
          'unknown': 0.0
      },
      'storage': {
          'hydro': -10.0,
      },
      'source': 'mysource.com'
    }
    """

    if target_datetime is None:
        target_datetime=arrow.now(tz='Chile/Continental')
        logger.warning('The real-time data collected by the parser is incomplete for the latest datapoints/hours,'
                       'so the last 3 datapoints were omitted.'
                       'If desired, please specify a historical date in YYYYMMDD format.')
    
    arr_target_datetime = arrow.get(target_datetime)
    start = arr_target_datetime.shift(days=-1).format("YYYY-MM-DD")
    end = arr_target_datetime.format("YYYY-MM-DD")

    date_component = 'fecha__gte={}&fecha__lte={}'.format(start, end)

    # required for access
    headers = {'Referer': 'https://www.coordinador.cl/operacion/graficos/operacion-real/generacion-real-del-sistema/',
               'Origin': 'https://www.coordinador.cl'}

    s = session or requests.Session()
    url = API_BASE_URL + date_component

    req = s.get(url, headers=headers)
    raw_data = req.json()['aggs']
    processed_data = data_processor(raw_data)

    data = []
    for production_data in processed_data:
        dt = production_data.pop('datetime')

        datapoint = {
            'zoneKey': zone_key,
            'datetime': dt,
            'production': production_data,
            'storage': {},
            'source': 'coordinador.cl'
            }

        data.append(datapoint)

    return data[:-9]
    """The last 9 datapoints should be omitted because they usually are incomplete and shouldn't appear on the map."""

if __name__ == "__main__":
    """Main method, never used by the Electricity Map backend, but handy for testing."""
    #print('fetch_production() ->')
    Prod=fetch_production()
    # For fetching historical data instead, try:
    #print(fetch_production(target_datetime=arrow.get("20200220", "YYYYMMDD")))
    
    wind=[]
    hydro=[]
    for item in Prod:
        try:
            wind.append(item['production']['wind'])
        except:
            wind.append('NaN')
        try:
            hydro.append(item['production']['hydro'])
        except:
            hydro.append('NaN')    
    
    #%%
    import matplotlib.pyplot as plt
    
    #%%
    plt.scatter(list(range(len(wind))),wind)

#%%
    plt.scatter(list(range(len(hydro))),hydro)

