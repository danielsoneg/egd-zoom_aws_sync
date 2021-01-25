import logging
import os
import boto3

import s3index

SITE_NAME = os.environ["SITE_NAME"]
S3_BUCKET = os.environ["S3_BUCKET"]
S3_OUTPUT_KEY = os.environ["S3_OUTPUT_KEY"]

LOG_LEVEL = os.environ["LOG_LEVEL"]
Log = logging.getLogger()
Log.setLevel(LOG_LEVEL)


def lambda_handler(*_):
    """This will be invoked either by a lambda function or by S3 delete. Because of that,
    we're ignoring both event and context."""
    Log.info("Checking bucket %s", S3_BUCKET)
    Log.info("Output Key: %s", S3_OUTPUT_KEY)
    bucket_location, objects = s3index.get_objects(S3_BUCKET)
    filtered = s3index.filter_objects(objects)
    by_date = s3index.order_objects(filtered)
    template = s3index.template_from_string(TEMPLATE)
    index = s3index.build_index(
        template, SITE_NAME, by_date, S3_BUCKET, bucket_location)
    s3_client = boto3.client("s3")
    s3_client.put_object(
        ACL="public-read",
        Body=index.encode(),
        Bucket=S3_BUCKET,
        Key=S3_OUTPUT_KEY,
        ContentType="text/html"
    )


# Template is here as a string for convenience. Could be an S3 object instead.
TEMPLATE = """
<html>
  <head>
    <title>{{ site_name }}</title>
  </head>
  <body>
    <h1>{{ site_name }}</h1>
    {%- for date, timestamps in dates %}
    <h3>{{ date.strftime("%B %d, %Y") }}</h3>
      {%- for datetime, files in timestamps %}
      <h4>{{ datetime.to("EST").format("H:mmZZZ") }}<h4>
      <ul>
        {%- for file in files %}
          <li><a href="http://{{ bucket }}.s3-website-{{ location }}.amazonaws.com/{{ file.key }}">{{ file.metadata["type"] }} ({{ file.metadata["size"] }})</a></li>
      {%- endfor %}
      </ul>
      {% endfor -%}
    {%- endfor %}
  </body>
</html>
"""
