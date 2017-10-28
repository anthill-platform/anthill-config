# Configuration Service
At some point, games may need some way be to dynamically configured server-side, 
so new build woulds not be required in order to update a configuration.

This service makes it possible by deploying the game configuration with 
[admin tool](https://github.com/anthill-platform/anthill-admin) and then by 
retrieving this configuration with client library.

The service handles the configuration as a plain file, so it's totally up to the game,
what configuration format should used, either JSON or binary.

As configuration files might grow in size, and even count in megabytes, this service allows the configurations to be
deployed onto a CDN, and cached locally to save bandwidth.

In other words, this service acts pretty much as a [DLC Service](https://github.com/anthill-platform/anthill-dlc),
except exactly the one file is downloaded.

## REST API

Please refer to the <a href="doc/API.md">API Documentation</a> for more information.
