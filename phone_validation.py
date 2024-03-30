import json
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# You may need to install Requests pip
# python -m pip install requests

class IPQS:
    key =  "nkqgbvZbkRrkSUoikha7lUSQlKEjubU5"
    def phone_number_api(self, phonenumber: str, vars: dict = {}) -> dict:
        url = 'https://www.ipqualityscore.com/api/json/phone/%s/%s' %(self.key, phonenumber)
        x = requests.get(url, params = vars)
        return (json.loads(x.text))
    
    def report_phonenumber_api(self, phonenumber: str, country: str, vars: dict = {}) -> dict:
        url = 'https://ipqualityscore.com/api/json/report/%s?country=%s&phone=%s' % (self.key, country, phonenumber)
        
        response = requests.get(url, params=vars)
        return response.json()


if __name__ == "__main__":
    """
    User's phone.
    """
    phone = '18007132618'

    #Retrieve additional (optional) data points which help us enhance fraud scores and ensure data is processed correctly.
    countries = {'US', 'CA', 'IN'};
        

    #custom feilds
    additional_params = {
        'country' : countries
    }

    """
    User & Transaction Scoring
    
    Score additional information from a user, order, or transaction for risk analysis
    Please see the documentation and example code to include this feature in your scoring:
    https://www.ipqualityscore.com/documentation/phone-number-validation-api/transaction-scoring
    This feature requires a Premium plan or greater
    """
    ipqs = IPQS()
    result  = ipqs.phone_number_api(phone, additional_params)

    # Check to see if our query was successful.
    if 'success' in result and result['success']:
        print("Phone Number Validated Successfully")
    else:
        print("Phone Number Validation Failed")
        print(result)
