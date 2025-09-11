import http.client

conn = http.client.HTTPSConnection("api.quiverquant.com")

headers = {
    'Accept': "application/json",
    'Authorization': "Bearer fde8b6bd5f6f33a84e921c7a55ed61538b93833c"
}

conn.request("GET", "/beta/bulk/congresstrading?date=20250903", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))