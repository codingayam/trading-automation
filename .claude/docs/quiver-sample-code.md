# Bulk Congress Trading (From Quiver)
get https://api.quiverquant.com/beta/bulk/congresstrading

## Request sample in python
import http.client

conn = http.client.HTTPSConnection("api.quiverquant.com")

headers = {
    'Accept': "application/json",
    'Authorization': "Bearer fde8b6bd5f6f33a84e921c7a55ed61538b93833c"
}

conn.request("GET", "/beta/bulk/congresstrading?date=20250918", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))

## Response Example
[
  {
    "Ticker": "string",
    "TickerType": "string",
    "Company": "string",
    "Traded": "2019-08-24T14:15:22Z",
    "Transaction": "string",
    "Trade_Size_USD": "string",
    "Status": "string",
    "Subholding": "string",
    "Description": "string",
    "Name": "string",
    "Filed": "2019-08-24T14:15:22Z",
    "Party": "string",
    "District": "string",
    "Chamber": "string",
    "Comments": "string",
    "excess_return": "string",
    "uploaded": null,
    "State": "string",
    "last_modified": null
  }
]

### Additional examples with real responses
[
  {
    "Ticker": "ROST",
    "TickerType": "ST",
    "Company": null,
    "Traded": "2025-08-18",
    "Transaction": "Purchase",
    "Trade_Size_USD": "1001.0",
    "Status": null,
    "Subholding": null,
    "Description": null,
    "Name": "Dan Newhouse",
    "BioGuideID": "N000189",
    "Filed": "2025-09-17",
    "Party": "R",
    "District": " WA04",
    "Chamber": "Representatives",
    "Comments": null,
    "Quiver_Upload_Time": null,
    "excess_return": "-3.37089934205417",
    "State": null,
    "last_modified": "2025-09-18"
  },
{
    "Ticker": "TGT",
    "TickerType": "ST",
    "Company": null,
    "Traded": "2025-08-18",
    "Transaction": "Purchase",
    "Trade_Size_USD": "1001.0",
    "Status": null,
    "Subholding": null,
    "Description": null,
    "Name": "Dan Newhouse",
    "BioGuideID": "N000189",
    "Filed": "2025-09-17",
    "Party": "R",
    "District": " WA04",
    "Chamber": "Representatives",
    "Comments": null,
    "Quiver_Upload_Time": null,
    "excess_return": "-19.4797367304365",
    "State": null,
    "last_modified": "2025-09-18"
  },
  ....
]


