###########
 Slack CLI
###########

Simple CLI tools for interacting with Slack.

-  ``slack_channels.py``: List Slack channels.
-  ``slack_files.py``: List and manipulate files downloaded from Slack to the file cache.
-  ``slack_history.py``: Display old messages for a channel.
-  ``slack_listen.py``: Listen for interactive Slack messages.
-  ``slack_post.py``: Send messages and / or files to a Slack channel.

*************************
 Deploying the Slack App
*************************

In order to use these CLI tools, you must first deploy a Slack app to a
workspace. The file ``manifest.yml`` can be imported. Browse to
https://api.slack.com/apps . Choose "Create New App" and select the
"From an app manifest" option. Follow the instructions to import the
app.

This process will grant permissions and event subscriptions to the app
that the CLI tools will need.

At the end of the process, you should have the tokens you need to grant
your app the required permissions. You will need both an App token and a
User token.

The App token can be found under your App's "Basic Information"
settings, in the section "App-Level Tokens". This token has the Slack
``connections:write`` permission, that allows the CLI tools to use
"Socket Mode". Socket Mode uses websockets rather than public HTTPS
endpoints to connect to the Slack APIs.

The User token can be found in the "Oauth & Permissions" feature for
your App, in the section "OAuth Tokens for Your Workspace".

These tokens need to be included in you workspace configuration file--
``$HOME/.slackcli/$WORKSPACE.toml``.

