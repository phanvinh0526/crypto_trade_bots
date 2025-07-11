# Login
heroku container:login

# Set container stack in Heroku
heroku stack:set container --app app-check-social-engagement

# Build and push image to Heroku
heroku container:push worker --app app-check-social-engagement

# Release the app
heroku container:release worker --app app-check-social-engagement

# Set env variables
heroku config:set VP_CHECK_SOCIAL_ENG_BOT=..... --app app-check-social-engagement
heroku config:set LUNA_CRUSH_API_TOKEN=... --app app-check-social-engagement

# Check logs
heroku logs --tail --app app-check-social-engagement

# ### Note ### #
# If the search CA does not work, check LunarCrush license, need to upgrade to Idividual subscription. And turn on Worker node on Heroku