import requests

def fetch_trades(address, api_key):
    url = "https://graphql.bitquery.io/"
    headers = {"Authorization": f"Bearer {api_key}"}
    query = """
    {
      ethereum(network: ethereum) {
        dexTrades(
          options: {desc: "block.height", limit: 10}
          baseCurrency: {is: "0xf3F496C9486BE5924a93D67e98298733Bb47057c"}
        ) {
          transaction {
            hash
          }
          tradeIndex
          smartContract {
            address {
              address
            }
            contractType
            protocolType
          }
          tradeAmount(in: USD)
          baseAmount
          baseCurrency {
            symbol
          }
          quoteAmount
          quoteCurrency {
            symbol
          }
          block {
            height
            timestamp {
              time(format: "%Y-%m-%d %H:%M:%S")
            }
          }
        }
      }
    }
    """
    response = requests.post(url, json={'query': query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed to run with a {response.status_code}. Error Message: {response.text}")

# Replace with your Bitquery API key
api_key = "ory_at_BoAVmjbOPbJSTpZBKre1ZqWNaPnaJU-8A9Hwn_Kgh3o.dl3xZXYGntSkAXxP4jLef1Wj0ua-yrr1TaoGWs2bNW0"
# Replace with the Ethereum address you're interested in
address = "0xf3F496C9486BE5924a93D67e98298733Bb47057c"

trades = fetch_trades(address, api_key)
print(trades)
