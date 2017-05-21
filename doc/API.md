
# REST API Requests

## Get the configuration

Returns the configuration for certain game version

#### ← Request

```rest
GET /config/<game-name>/<game-version>
```

| Argument         | Description                                                              |
|------------------|--------------------------------------------------------------------------|
| `game-name`      | A name of the game to receive the config about                           |
| `game-version`   | Game version                                                             |

Since often the configuration is needed before authorization, no access token is required.

#### → Response

In case of success, a complete configuration JSON object is returned 
(with `Content-Type` defined as `application/json`):
```json
{
  "property-a": "test", 
  "property-b": true, 
  "property-c": 50
}
```

**Warning**: Instead returning a configuration, a redirection to a CDN service may happen, so the
client who requests the configuration must follow redirects.

| Response             | Description                                          |
|----------------------|------------------------------------------------------|
| `200 OK / 302 Found` | Everything went OK, configuration follows.           |
| `404 Not Found`      | No such configuration or game                        |
