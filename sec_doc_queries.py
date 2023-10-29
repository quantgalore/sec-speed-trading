# -*- coding: utf-8 -*-
"""
Created on Thu Oct 19 16:28:13 2023

@author: Local User
"""

import pandas as pd
import numpy as np
import requests

from sec_api import QueryApi, XbrlApi, ExtractorApi
from sec_doc_functions import summarizer, transform_string
from datetime import datetime, timedelta

# user agent format is companyname/version contact_name@website.com
user_agent = "MyCompany/1.0 john@pyrex.com"
sec_api_key = "4914da567d5749478846ddda2492107c66fb0cddeb04ae6c835b93e951c7cfde"
polygon_api_key = "your polygon.io API key"

queryApi = QueryApi(api_key=sec_api_key)
xbrlApi = XbrlApi(sec_api_key)
extractorApi = ExtractorApi(sec_api_key)

date = datetime.today().strftime("%Y-%m-%d")

# get the 100 latest 8-K filings that reflect new information changes (we exclude updates to prior announcement)

filings_data_list = []

for iteration in range(0,100, 50):

    query = {
      "query": { "query_string": { 
          "query": "formType:\"8-K\"",
      } },
      "from": f"{iteration}",
      "size": "50",
      "sort": [{ "filedAt": { "order": "desc" } }]
    }
    
    response = queryApi.get_filings(query)
    
    filings_data = pd.json_normalize(response["filings"]).replace('', np.nan).dropna(subset="ticker")
    filings_data["filedAt"] = pd.to_datetime(filings_data["filedAt"].values)
    filings_data["filing_date"] = pd.to_datetime(filings_data["filedAt"].values).strftime("%Y-%m-%d")
    filings_data = filings_data[filings_data["periodOfReport"] == filings_data["filing_date"]]
    filings_data = filings_data[filings_data["filing_date"] == date]
    filings_data_list.append(filings_data)
    
filings_data = pd.concat(filings_data_list)

# get the summaries and scores of each filing. Exclude earnings and director changes

summary_and_score_list = []

for filing in filings_data["id"]:
    filing = filings_data[filings_data["id"] == filing]
    items = filing["items"].iloc[0]
    
    item_strings = []
    
    for item in items:
        
        transformed_item = transform_string(item)
        if (transformed_item == "9-1") or (transformed_item == "2-2") or (transformed_item == "5-2"):
            continue
        
        item_strings.append(transformed_item)
    
    filing_url = filing["linkToHtml"].iloc[0]
    
    section_text_list = []
    
    for item_string in item_strings:
        section_text = extractorApi.get_section(filing_url, item_string, "text")
        
        section_text_list.append(section_text)
    
    summary_list = []
    
    for filing_text in section_text_list:
        
        summary = summarizer(filing_text)
        summary["ticker"] = filing["ticker"].iloc[0]
        summary["filedAt"] = filing["filedAt"].iloc[0]
        summary["periodOfReport"] = filing["periodOfReport"].iloc[0]
        print(f"\n{summary['summary']}")
        
        summary_list.append(summary)
    
    summaries = pd.DataFrame(summary_list)
    summary_and_score_list.append(summaries)

complete_summaries = pd.concat(summary_and_score_list)

# get the latest performance of the respective tickers, exclude penny stocks and those non-optionable

tickers = complete_summaries["ticker"].drop_duplicates().values

ticker_data_list = []

for ticker in tickers:
    
    try:
    
        underlying = pd.json_normalize(requests.get(f"https://api.polygon.io/v2/last/nbbo/{ticker}?apiKey={polygon_api_key}").json()["results"]).set_index("t").rename(columns={"P":"ask", "p":"bid"})
        underlying.index = pd.to_datetime(underlying.index, unit = "ns", utc = True).tz_convert("America/New_York")
        
        prior_underlying = pd.json_normalize(requests.get(f"https://api.polygon.io/v2/aggs/ticker/{ticker}/prev?apiKey={polygon_api_key}").json()["results"]).set_index("t")
        prior_underlying.index = pd.to_datetime(prior_underlying.index, unit = "ms", utc = True).tz_convert("America/New_York")
        
        ticker_call_contracts = pd.json_normalize(requests.get(f"https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={ticker}&contract_type=call&as_of={date}&expired=false&limit=1000&apiKey={polygon_api_key}").json()["results"])
        expiration_date = ticker_call_contracts[ticker_call_contracts["expiration_date"] >= date]["expiration_date"].iloc[0]
        
        current_price = round((underlying["bid"].iloc[0] + underlying["ask"].iloc[0]) / 2, 2)
        prior_price = prior_underlying["c"].iloc[0]
        
        returns = round(((current_price - prior_price) / prior_price), 2)
        
        ticker_dataframe = pd.DataFrame([{"ticker": ticker, "returns": returns, 'exp_date': expiration_date}])
        ticker_data_list.append(ticker_dataframe)
    except Exception as error:
        print(ticker, error)
        continue
    
full_ticker_data = pd.concat(ticker_data_list)

summaries_and_prices = pd.merge(complete_summaries, full_ticker_data, on = "ticker")
    
