# Login
heroku container:login

# Set container stack in Heroku
heroku stack:set container --app hyperliquid-wallet-tracking

# Build and push image to Heroku
heroku container:push worker --app hyperliquid-wallet-tracking

# Release the app
heroku container:release worker --app hyperliquid-wallet-tracking

# Set env variables
heroku config:set VP_CHECK_HYPERLIQUID_BOT=... --app hyperliquid-wallet-tracking
heroku config:set VP_CRYPTO_GROUP_CHAT_ID=-1002229815206 --app hyperliquid-wallet-tracking
heroku config:set VP_CRYPTO_GROUP_CHAT_TOPIC_ID=27963 --app hyperliquid-wallet-tracking
heroku config:set VP_PERIODICAL_CHECK_TIME=3600 --app hyperliquid-wallet-tracking

heroku config:set VP_USER_ADDRESSES=0x20c2d95a3dfdca9e9ad12794d5fa6fad99da44f5,0xf3f496c9486be5924a93d67e98298733bb47057c,0x899c0eef91d624cc4debab1ced1f05d89132d15a,0x24fb6523036ebcb3cc51deff138066dccf6bed0f,0x0ecd8a50ce988862dc0e69a669159036e88ea649,0x7dacca323e44f168494c779bb5e7483c468ef410,0xceec48581b3145a575508719f45da07dc57fa7ce,0xf28e1b06e00e8774c612e31ab3ac35d5a720085f,0xa4dedda59f2908b92ae192cfd494839373bcb3c4,0x9e8b1e51c642f4c8b87c6ba11c53d516a218afc4,0xBb876071A63Bc4D9bfCf46B012b4437Ea7Ff4281,0x15b325660a1c4a9582a7d834c31119c0cb9e3a42,0xB83DE012dbA672c76A7dbbbf3E459CB59D7D6E36,0x5078c2fbea2b2ad61bc840bc023e35fce56bedb6 --app hyperliquid-wallet-tracking

# ############################################### #
# Check logs
heroku logs --tail --app hyperliquid-wallet-tracking

# Create standard scheduler
heroku addons:create scheduler:standard --app hyperliquid-wallet-tracking

# Open a scheduler
heroku addons:open scheduler

# Turn on worker
heroku ps:scale worker=1 -a hyperliquid-wallet-tracking

# Turn off worker
heroku ps:scale worker=0 -a hyperliquid-wallet-tracking
