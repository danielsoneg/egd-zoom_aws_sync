import logging
import os
import boto3
import zoom_sync
from zoom_sync import zoom
from zoom_sync import s3

ZOOM_ISS = os.environ["ZOOM_ISS"]
ZOOM_SECRET = os.environ["ZOOM_SECRET"]
ZOOM_WEBHOOK_AUTH = os.environ["ZOOM_WEBHOOK_AUTH"]
ZOOM_USER_EMAIL = os.environ["ZOOM_USER_EMAIL"]

S3_BUCKET = os.environ["S3_BUCKET"]

NEXT_LAMBDA = os.environ.get("NEXT_LAMBDA")

LOG_LEVEL = os.environ["LOG_LEVEL"]
Log = logging.getLogger()
Log.setLevel(LOG_LEVEL)


class Unauthorized(Exception):
    """Raised when the auth header is incorrect"""


class BadUser(Exception):
    """Raised when the desired user cannot be found"""


def parse_web_callback(event, zoom_client):
    if event["params"]["header"].get("Authorization") != ZOOM_WEBHOOK_AUTH:
        raise Unauthorized("Bad auth token")
    body = event["body-json"]
    download_token = body["download_token"]
    meeting_data = body["payload"]["object"]
    return [zoom.Meeting(zoom_client, meeting_data, download_token=download_token), ]


def sync_zoom_meetings(event, zoom_client):
    zoom_uid = zoom_client.get_userid(ZOOM_USER_EMAIL)
    if not zoom_uid:
        raise BadUser("Cannot find user for email %s" % ZOOM_USER_EMAIL)
    return zoom_client.get_meetings_with_recordings(zoom_uid)


def upload_meeting_recordings(meetings):
    s3_uploader = s3.S3Uploader(S3_BUCKET, log=Log)
    full_count = 0
    for meeting in meetings:
        Log.info("Uploading %s recordings from meeting %s on %s",
                 len(meeting.recordings),
                 meeting.id,
                 meeting.start.format("YYYY-MM-DD"))
        count = s3_uploader.upload_recordings(meeting.recordings)
        full_count += count
    Log.info("Done uploading, %d successful uploads", full_count)
    return full_count


def lambda_handler(event, context):
    Log.debug(event)
    zoom_client = zoom.Zoom(ZOOM_ISS, ZOOM_SECRET)
    if event.get("source") == "aws.apigateway":
        Log.debug("Web call")
        meetings = parse_web_callback(event, zoom_client)
    else:
        Log.debug("Not a web call, syncing all")
        meetings = sync_zoom_meetings(event, zoom_client)
    Log.info("Found %d meetings with recordings.", len(meetings))
    full_count = upload_meeting_recordings(meetings)
    Log.info("Uploaded %d total files", full_count)
    if full_count and NEXT_LAMBDA:
        Log.info("Issuing event to %s", NEXT_LAMBDA)
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName=NEXT_LAMBDA,
            InvocationType="Event",
            LogType="Tail"
        )
