# Zoom to AWS Sync
Set of scripts & lambda functions to sync Zoom recordings to S3 and build an http index.

*Note: These scripts are provided as-is, and should not be considered production-ready. Among the deficiencies are limited documentation and missing tests.*

To build and deploy these lambda functions, follow the instructions on Amazon:

https://docs.aws.amazon.com/lambda/latest/dg/python-package.html

# `zoom_sync`
Lambda script to sync recordings between a Zoom account and an S3 bucket. Can work with Zoom web hooks, on a schedule, or both. Script is designed so files can be rehosted from S3. Recordings are saved to S3 using their Zoom IDs with ContentDisposition set to a constructed filename.

## Lambda Environment Variables
The script requires several environment variables:
* `LOG_LEVEL` - INFO or DEBUG
* `ZOOM_ISS` - Zoom API Key (Named 'ISS' to match JWT spec)
* `ZOOM_SECRET` - Zoom API Secret
* `ZOOM_WEBHOOK_AUTH` - Zoom webhook verification token
* `ZOOM_USER_EMAIL` - Email of the Zoom account to sync from
* `S3_BUCKET` - Name of the s3 bucket to sync to
* `NEXT_LAMBDA` - If set, this lambda will be called when new videos are synced. Should be set to the name of the lambda function set up for the s3index script below.

## Notes

The app uses JWT to authenticate to Zoom. You must sign up for a developer account, create an app, and generate the token key and secret. It also relies on the "New Recordings" event subscription, and will need the verification token.

Because the script can take time to run, it should be put behind an AWS Rest API Gateway. Follow instructions on Amazon:

https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-lambda-integration-async.html

Similarly, you'll want to forward the "Authorization" header through the API gateway so the lambda function has access.

# `s3index`
Lambda script to read a given S3 bucket, find media files with the required metadata, and generate an HTML index with readable names and links.

The HTML template used to generate the index is included as a string in `lambda_function.py`. Externalizing this file is left as an exercise for the reader.

The `s3index` script can also be run separately as a CLI script, saving the index file to the local disk.

## Lambda Environment Variables
* `LOG_LEVEL` - Same as above, INFO or DEBUG
* `S3_BUCKET` - The bucket to scan for files to index
* `S3_OUTPUT_KEY` - The S3 key to save the index into. Note the index will be saved to the bucket specified in `S3_BUCKET`.
* `SITE_NAME` - Used as the title in the included template.

## Notes
As set up, the lambda function will save the index to the same bucket as it reads from - so it is a Bad Idea to trigger this lambda based on files being added or changed in the bucket.
