# Configuration Service
At some point, games may need some way be to dynamically configured server-side, 
so new build would not be required in order to update a configuration.

This service makes it possible by editing the game configuration with 
[admin tool](https://github.com/anthill-services/anthill-admin) and then by 
retrieving this configuration with client library.

As editing a raw JSON may lead to misconfiguration issues, the 
[JSON Schema](https://spacetelescope.github.io/understanding-json-schema/index.html) 
validation is used upon editing. So, for example,

<details>
  <summary>that schema <i>(expandable)</i></summary><p>
  
```json
    {
        "title": "A game configuration",
        "type": "object",
        "properties": {
            "property-b": { 
                "type": "boolean", 
                "propertyOrder": 2, 
                "format": "checkbox", 
                "title": "The Second Property" 
            },
            "property-c": { 
                "type": "number", 
                "propertyOrder": 3, 
                "title": "The Third Property" 
            },
            "property-a": { 
                "type": "string", 
                "propertyOrder": 1, 
                "title": "The First Property" 
            }
        }
    }
```
</p></details>
<br>
Is edited <b>that</b> easy:
<br><br>
<img width="529" alt="configuration" src="https://cloud.githubusercontent.com/assets/1666014/26252695/a588ad7c-3cb9-11e7-9c11-b8383e3d6ed9.png">

And after the edit, that JSON configuration object will be generated:

```json
{
  "property-a": "test", 
  "property-b": true, 
  "property-c": 50
}
```

## REST API

Please refer to the <a href="doc/API.md">API Documentation</a> for more information.

## Configuration process

Configuration process takes these steps:

1. A [JSON Schema](https://spacetelescope.github.io/understanding-json-schema/index.html) is defined 
either on a certain game version or for the whole game itself;
2. The corresponding configuration is edited using visual editor;
3. Then the configuration is received by client using simple API call.

