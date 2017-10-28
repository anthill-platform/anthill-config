
# REST API Requests

## Get the configuration

Returns the configuration for certain game version

#### ← Request

```rest
GET /config/<game-name>/<game-version>?gamespace=<gamespace>
```

| Argument         | Description                                                              |
|------------------|--------------------------------------------------------------------------|
| `game-name`      | A name of the game to receive the config about                           |
| `game-version`   | Game version                                                             |
| `gamespace`      | Name of the gamespace to get the configuration about, see <a href="https://github.com/anthill-platform/anthill-login#gamespace">gamespace</a> |

Since often the configuration is needed before authorization, no access token is required. 
But plain <a href="https://github.com/anthill-platform/anthill-login/blob/master/doc/API.md#authenticate">gamespace alias</a> is required instead.

#### → Response

In case of success, a complete configuration JSON object is returned 
(with `Content-Type` defined as `application/json`):
```json
{
  "url": "<configuration file location over the internet>", 
  "id": <id of the configuration>
}
```

After the configuration information is received, the client must download the configuration at `url`,
and possibly cache it, using `id` as the key. On subsequent calls, befor downloading, the client much check for the
cache using the `id` field.

| Response             | Description                                          |
|----------------------|------------------------------------------------------|
| `200 OK / 302 Found` | Everything went OK, configuration info follows.           |
| `404 Not Found`      | No such configuration or game                        |
