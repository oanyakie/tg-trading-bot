from binance.client import Client
client = Client(api_key="1ZdmnuIhGUwmD43exIyW8zrPQkk9lULLDY1zX1jpDYoWTXRnBbxurKs6chlMCCLg" ,api_secret="HtoTg6vCbBy5MqXJFygIYoICD4pRjRzIvuBJnwaprMkTEDkCQELozVVeCajtWUjE")
status = client.get_account_api_permissions()
print(status)