# Mock KBase Core Services

Declare mock endpoints in a single JSON configuration, then run the server in a
tiny alpine docker image.

## Quick start

### Writing the endpoints.json file

First, write JSON configuration files that define some endpoints and canned
responses.

The following example defines two mock responses for an authentication service
-- one for an invalid user, and one for a valid user.

`authorized_whoami.json`

```json
{
  "methods": ["GET"],
  "path": "/whoami",
  "headers": { "Authorization": "Bearer valid_user_token" },
  "response": {
    "status": "200",
    "body": "valid_user_name"
  }
}
```

`unauthorized_whoami.json`

```json
{
  "methods": ["GET"],
  "path": "/whoami",
  "headers": { "Authorization": "Bearer invalid_user" },
  "response": {
    "status": "403",
    "body": "Unauthorized"
  }
}
```

Each mock config file has the following properties:

- `request` - required - object containing request filtering properties
  - `method` - required - array of string - matches if any of the methods in the
    provided array match the method of the request
  - `path` - required - string - matches if the provided path string matches the
    request path exactly
  - `headers` - optional - object - matches if all provided header fields are
    present and match (exact string match) in the request
  - `absent_headers` - optional - array of string - matches if the provided
    header fields are not present in the request
  - `body` - optional - string | object - request body to match against
- `response` - required - object containing the
  - `status` - optional (defaults to 200) - string - the status of the response
  - `body` - optional - string or object - the response content
  - `headers` - optional - object - response headers

Any requests that are made to the server that do not match any config file
respond with a 500 status.

Check the server logs to debug requests that don't match any endpoints you have
defined in your configs.

### Running the docker image

Run the docker image `kbase/mock_service` with your config file directory
mounted to `/config` inside the container.

```sh
docker run -p 5000:5000 -v "$(pwd)/test/mock_service:/config" kbase/mock_service
```

Where `$(pwd)/test/mock_service` contains your json configuration files.

The above runs a simple python server **exposed on port 5000** that validates
your configuration and accepts (or denies) requests according to your mocked
endpoints.

It can be handy in a project which uses `mock_service` to utilize a
docker-compose to run the mock services in conjunction with the service of
interest. Here is an example where we define a mock service alongside other
ones:

```yaml
version: '3'

# This docker-compose is for testing

services:

  # For running the app server
  web:
    build: . 
    ...

  # A mock auth server (see test/mock_auth/endpoints.json)
  auth:
    image: kbase/mock_service
    ports:
      - 5000:5000
    volumes:
      - ${PWD}/test/mock_auth:/config
```

## Development

### set up Python

For example, using stock Python and its virtual environment support:

```bash
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Using docker

#### make image

```bash
docker build -t kbase-mock-service .
```

#### Run it

```bash
docker run --rm -p 5000:5000 -v `pwd`/examples:/config kbase-mock-service
```

Quit it with Ctrl-C

### Using docker-compose

```bash
docker-compose run -v `pwd`/examples:/config --rm kbase-mock-service
```

Quit it with Ctrl-C

## TODO

- review documentation to ensure that behavior is as described; I'm pretty sure
  it is wrong in places
- add tests
- GHA test, build, push image
- allow DEBUG to be provided by shell environment variables; and document this
  behavior
