import os
import sys
import json
import jsonschema
import traceback
import flask
from jsonschema.exceptions import ValidationError

# Load the endpoints data, the schema, and validate the structure
DEBUG = False

# For validating every config file
def load_endpoints():
    if not os.path.exists("/config"):
        sys.stderr.write("Path not found: /config\n")
        # TODO: explain a bit more; tell user how to fix this.
        sys.exit(1)

    schema_path = f"{os.path.dirname(__file__)}/../schemas/endpoint_schema.json"
    with open(schema_path) as fd:
        endpoint_schema = json.load(fd)

    endpoints = []
    for path in os.listdir("/config"):
        if path.endswith(".json"):
            full_path = "/config/" + path
            with open(full_path) as fd:
                try:
                    endpoint = json.load(fd)
                except ValueError as err:
                    sys.stderr.write(f'Error parsing "{full_path}" as JSON:\n{err}')
                    sys.exit(1)
                try:
                    jsonschema.validate(endpoint, endpoint_schema)
                except ValidationError as err:
                    sys.stderr.write(f"JSON Schema validation Error for {path}:\n")
                    sys.stderr.write(str(err) + "\n")
                    sys.exit(1)
                endpoints.append(endpoint)
    return endpoints


def match_headers(endpoint):
    """
    Either check that there are no headers to match, or match that all headers
    in the endpoint are present and equal in the request.
    """
    if "headers" not in endpoint and "absent_headers" not in endpoint:
        return True
    headers = dict(flask.request.headers)
    if "headers" in endpoint:
        for (key, val) in endpoint["headers"].items():
            if val != headers.get(key):
                return False
    # Enforce that certain headers must be absent
    if "absent_headers" in endpoint:
        header_keys = set(key.lower() for key in headers.keys())
        message("headers are", headers)
        for key in endpoint["absent_headers"]:
            message("checking absent", key)
            if key.lower() in header_keys:
                return False
    return True


def mock_response(response):
    """
    Create a mock flask response from the endpoint response
    """
    resp_body = response.get("body")
    if isinstance(resp_body, dict):
        resp_body = json.dumps(resp_body, indent=4)
    resp = flask.Response(resp_body)

    resp.status = response.get("status", 200)

    for (header, val) in response.get("headers", {}).items():
        resp.headers[header] = val

    return resp


def get_env_var_boolean(name, default_value):
    value = os.environ.get(name, "").strip()
    if len(value) == 0:
        return default_value
    return value.lower()[0] in ["t", "1"]


def message(*msgs):
    if DEBUG:
        for msg in msgs:
            print(msg)


# This complies with the recommended (or canonical, at least) method for supplying an
# app factory function (which is canoncially named 'create_app'.)
def create_app():
    global DEBUG
    DEBUG = get_env_var_boolean("DEBUG", False)

    endpoints = load_endpoints()
    message(f"Loaded {len(endpoints)} mock endpoints")

    # Start the Flask app
    app = flask.Flask(__name__)

    methods = ["GET", "POST", "PUT", "DELETE"]

    @app.route("/", defaults={"path": ""}, methods=methods)
    @app.route("/<path:path>", methods=methods)
    def handle_request(path):
        """
        Catch-all: handle any request against the endpoints.json data.
        """
        message("-" * 80)
        path = "/" + path
        req_body = flask.request.get_data().decode() or ""
        method = flask.request.method
        # Find the first endpoint that matches path, method, headers, and body
        for endpoint in endpoints:
            request_matcher = endpoint["request"]
            # Match path
            if request_matcher["path"] != path:
                message(
                    f'Path "{path}" does not match request filter path "{request_matcher["path"]}"'
                )
                continue

            # Match request method
            expected_methods = request_matcher.get("methods")
            if method not in expected_methods:
                message(f"Mismatch on method: {method} vs {expected_methods}")
                continue

            # Match on header
            if not match_headers(request_matcher):
                hs = dict(flask.request.headers)
                expected_hs = request_matcher.get("headers")
                message(
                    f"Mismatch on headers:\n  got:      {hs}\n  expected: {expected_hs}"
                )
                continue

            # Match on body
            expected_body = request_matcher.get("body", "")
            if isinstance(expected_body, dict):
                # Compare JSON values (as JSON string)
                expected_body_json = json.dumps(expected_body)
                try:
                    given_body_json = json.dumps(json.loads(req_body))
                except Exception as err:
                    message("Error parsing json body:", str(err))
                    continue
                body_ok = expected_body_json == given_body_json
            else:
                # Compare string values
                body_ok = expected_body.strip() == req_body.strip()
            if not body_ok:
                message(
                    f"Mismatch on body:\n  got: {req_body}\n  expected: {expected_body}"
                )
                continue

            # If get here, everything matches.
            message("Matched endpoint {} {}".format(method, path))
            return mock_response(endpoint.get("response"))

        raise Exception("Unable to match endpoint: %s %s" % (method, path))

    @app.errorhandler(Exception)
    def any_exception(err):
        """Catch any error with a JSON response."""
        class_name = err.__class__.__name__
        message(traceback.format_exc())
        resp = {"error": str(err), "class": class_name}
        return (flask.jsonify(resp), 500)

    return app
