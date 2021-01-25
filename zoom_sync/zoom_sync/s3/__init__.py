import boto3
import arrow
import tempfile
import logging


class S3Uploader:
    def __init__(self, bucket, log=None):
        self.bucket = bucket
        self.client = boto3.client("s3")
        self.log = log or logging.getLogger()

    def get_current_object_keys(self):
        resp = self.client.list_objects_v2(Bucket=self.bucket)
        return set(obj["Key"] for obj in resp["Contents"] if "Key" in obj)

    def upload_recordings(self, recordings):
        current_objs = self.get_current_object_keys()
        count = 0
        for recording in recordings:
            if recording.id in current_objs:
                self.log.info(
                    "REC %s: already present, skipping", recording.id)
                continue
            try:
                self.upload(recording)
            except Exception:
                continue
            else:
                count += 1
        return count

    def upload(self, recording):
        handle = recording.get_handle()
        self.log.info("REC %s: '%s' Starting upload...",
                      recording.id, recording.name)
        upload = self.client.create_multipart_upload(
            Bucket=self.bucket,
            Key=recording.id,
            StorageClass="INTELLIGENT_TIERING",
            Metadata=recording.meta,
            ContentDisposition="attachment; filename=\"%s\"" % recording.name
        )
        upload_id = upload["UploadId"]
        self.log.info("REC %s: Multipart Upload ID: %s",
                      recording.id, upload_id)
        parts = []
        try:
            idx = 0
            for idx, chunk in enumerate(handle.iter_content(chunk_size=10*1024*1024), start=1):
                self.log.debug("REC %s UPLOAD %s: Part %s",
                               recording.id, upload_id, idx)
                resp = self.client.upload_part(
                    Body=chunk,
                    Bucket=self.bucket,
                    Key=recording.id,
                    UploadId=upload_id,
                    PartNumber=idx,
                )
                parts.append({"PartNumber": idx, "ETag": resp['ETag']})
        except Exception as err:
            self.log.exception(
                "REC %s: Error uploading part %d", recording.id, idx)
            try:
                self.client.abort_multipart_upload(
                    Bucket=self.bucket,
                    Key=recording.id,
                    UploadId=upload_id,
                )
            except Exception as abort_err:
                self.log.exception(
                    "REC %s: FAILED TO ABORT UPLOAD!", recording.id)
                self.log.warn(" . You must manually abort the upload!")
                self.log.warn(" . Upload ID: %s", upload_id)
            else:
                self.log.info(" . Successfully aborted upload.")
            finally:
                raise err
        else:
            self.log.info(
                "REC %s: All parts uploaded, completing upload...", recording.id)
            resp = self.client.complete_multipart_upload(
                Bucket=self.bucket,
                Key=recording.id,
                MultipartUpload={"Parts": parts},
                UploadId=upload_id,
            )
            self.log.info("REC %s: Finished uploading item: %s",
                          recording.id, resp["ETag"])
