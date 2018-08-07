import logging
import xdrlib
import pandas as pd
import sensorcloud as sc

SENSOR_NAME = 'LeGrand'
CHANNEL_NAME = 'kWh'

def processLeGrandFile(file):
    logger = logging.getLogger('solaroad.legrand')

    x = pd.read_csv(file, delimiter=';', skip_blank_lines=True)
    x.columns = ['Date', 'kWh']
    index_time = pd.to_datetime(x['Date'], format='%m/%d/%Y %I:%M:%S %p')

    x.index = index_time
    for key in x.keys():
        if 'Unnamed' in key:
            del (x[key])
    x = x.dropna()
    del (x['Date'])
    x['kWh'] = pd.to_numeric(x['kWh'])

    # Authenticate
    server, auth_token = sc.authenticate()
    deviceId = sc.getDeviceId()

    # Add Sensor
    logger.debug('======================== Now processing Legrand ========================')
    sc.addSensor(server, auth_token, deviceId, SENSOR_NAME, SENSOR_NAME, SENSOR_NAME, SENSOR_NAME)

    # Pre-processing
    y = x.resample('12H').mean().interpolate(method='linear')

    # Break DataFrame into chunks of 100k
    ctr = 0
    total_steps = round(len(x) / sc.MAX_POINTS) + 1
    while ctr < total_steps:
        sp = ctr * sc.MAX_POINTS
        tmp = y.iloc[sp:sp + sc.MAX_POINTS - 1, :]
        logger.debug('--------------------- RECORD %s/%s ------------------------------', ctr + 1, total_steps)
        for key in tmp.keys():
            packer = xdrlib.Packer()
            packer.pack_int(1)  # version 1

            packer.pack_enum(sc.SECONDS)
            packer.pack_int(43200)

            POINTS = len(tmp[key])
            packer.pack_int(POINTS)

            logger.debug('Now uploading %s', key)

            if ctr == 0:
                sc.addChannel(server, auth_token, deviceId, SENSOR_NAME, CHANNEL_NAME, CHANNEL_NAME, CHANNEL_NAME)

            for item in tmp[key].iteritems():
                val = item[1]
                timestamp = item[0].to_pydatetime().timestamp() * 1000000000
                packer.pack_hyper(int(timestamp))
                packer.pack_float(float(val))

            data = packer.get_buffer()
            sc.uploadData(server, auth_token, deviceId, SENSOR_NAME, CHANNEL_NAME, data)
        ctr = ctr + 1
