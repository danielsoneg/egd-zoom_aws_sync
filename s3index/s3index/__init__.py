from jinja2 import Template
import arrow
import boto3
import click

REQUIRED_METADATA = ("timestamp", "type", "size")


def filter_objects(objects):
    for obj in objects:
        meta = obj.metadata
        if all(key in meta for key in REQUIRED_METADATA):
            yield obj


def order_objects(objects):
    dates = {}
    for obj in objects:
        meta = obj.metadata
        timestamp = int(meta["timestamp"])
        datetime = arrow.get(timestamp)
        date = datetime.date()
        if date not in dates:
            dates[date] = {}
        if datetime not in dates[date]:
            dates[date][datetime] = []
        dates[date][datetime].append(obj)
    for date in dates.values():
        for datetime in date.values():
            # Hack to get consistent order
            datetime.sort(key=lambda i: -i.content_length)
    by_date = []
    for date, datetimes in sorted(dates.items(), key=lambda i: i[0]):
        by_date.append((date, sorted(datetimes.items(), key=lambda i: i[0])))
    return by_date


def get_objects(bucket):
    s3_client = boto3.client("s3")
    s3_rsc = boto3.resource("s3")
    bucket_location = s3_client.get_bucket_location(Bucket=bucket)[
        "LocationConstraint"]
    bucket_rsc = s3_rsc.Bucket(bucket)
    return bucket_location, [obj.Object() for obj in bucket_rsc.objects.iterator()]


def template_from_string(template_string):
    """I mostly just don't want to import jinja bits outside this script"""
    return Template(template_string)


def template_from_file(template_fn):
    with open(template_fn) as fh:
        template = Template(fh.read())
    return template


def build_index(template, site_name, by_date, bucket, location):
    index = template.render(
        site_name=site_name,
        dates=by_date,
        bucket=bucket,
        location=location)
    return index


@ click.command()
@ click.argument("bucket")
@ click.argument("site_name")
@ click.option("-t", "--template", default="./index.html.template", help="Template file")
@ click.option("-o", "--output", default="./index.html", help="Destination file")
@ click.option("--debug", is_flag=True, help="Print template output instead of writing to file")
def main(bucket, template, site_name, output, debug):
    """Build an index file for an S3 bucket"""
    bucket_location, objects = get_objects(bucket)
    by_date = order_objects(filter_objects(objects))
    template = template_from_file(template)
    index = build_index(template, site_name, by_date,
                        bucket, bucket_location)

    if debug:
        print(index)
    else:
        with open(output, "w") as fh:
            fh.write(index)


if __name__ == "__main__":
    main()
