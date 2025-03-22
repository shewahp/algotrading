import credentials as crs

# Import the required module from the fyers_apiv3 package
from fyers_apiv3 import fyersModel
import pandas as pd

client_id = crs.client_id
secret_key = crs.secret_key
redirect_uri = crs.redirect_uri
with open('access.txt') as f:
	access_token =f.read()

exchange='NSE'
sec_type='EQ'
symbol='RELIANCE'

ticker=f"{exchange}:{symbol}-{sec_type}"
print(ticker)


# Initialize the FyersModel instance with your client_id, access_token, and enable async mode
fyers = fyersModel.FyersModel(client_id=client_id, is_async=False, token=access_token, log_path="")

data = {
    "symbol":"NSE:SBIN-EQ",
    "resolution":"D",
    "date_format":"0",
    "range_from":"1690895316",
    "range_to":"1691068173",
    "cont_flag":"1"
}

response = fyers.history(data=data)
print(response)
