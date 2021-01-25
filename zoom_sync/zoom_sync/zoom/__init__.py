import logging
import arrow
import datetime
import requests
from humanize import filesize
from jose import jwt

class Zoom:
    class RequestFailed(Exception):
        """Raised when requests fail"""

    def __init__(self, iss, key):
        self.__iss = iss
        self.__key = key

    def __get_token(self):
        exp = datetime.datetime.utcnow() + datetime.timedelta(seconds=5)
        payload = {
            "iss": self.__iss,                  # Issuer
            "exp": exp,                         # Expiration
            "iat": datetime.datetime.utcnow(),  # Issued
        }
        return jwt.encode(payload, self.__key)

    def __get_headers(self):
        return {"authorization": "bearer %s" % self.__get_token(),
                "content-type": "application/json"}

    def build_url(self, path, version="v2"):
        path = path.lstrip("/")
        return "https://api.zoom.us/%(version)s/%(path)s" % {"version": version, "path": path}

    def __request(self, method, path, params):
        url = self.build_url(path)
        resp = requests.request(
            method, url, params=params, headers=self.__get_headers())
        if resp.status_code == 200:
            return resp.json()
        else:
            raise Zoom.RequestFailed("Request failed: %s: %s" %
                                     (resp.status_code, resp.text))

    def get(self, path, params=None):
        return self.__request("get", path, params)

    def post(self, path, params=None):
        return self.__request("post", path, params)

    def delete(self, path):
        return self.__request("delete", path, None)

    def get_userid(self, email=None):
        users = self.get("users")["users"]
        if email:
            try:
                return next(u for u in users if u.get(
                    "email") == email)["id"]
            except StopIteration:
                return None
        else:
            return users[0]["id"]

    def get_meetings_with_recordings(self, user, days=30, page_token=None):
        from_date = (datetime.date.today() -
                     datetime.timedelta(days=days)).strftime("%Y-%m-%d")
        params = {"from": from_date, "page_size": 300}
        return [Meeting(self, data) for data in
                self.get("users/%s/recordings" % user, params=params)["meetings"]]

    def get_recording(self, recording, access_token=None):
        resp = requests.get(recording.url, stream=True,
                            params={"access_token": access_token or self.__get_token()})
        if resp.status_code != 200:
            raise Zoom.RequestFailed("Request failed: %s: %s" %
                                     (resp.status_code, resp.text))
        return resp
        # with open("./%s" % recording.name, "wb") as fh:
        #    for chunk in resp.iter_content(chunk_size=128):
        #        fh.write(chunk)


class Meeting:
    def __init__(self, client, data, download_token=None):
        self.__zoom = client
        self.uuid = data["uuid"]
        self.id = data["id"]
        self.start = arrow.get(data["start_time"])
        self.end = self.start.shift(minutes=data["duration"])
        self.token = download_token
        self.recordings = [Recording(self.__zoom, self, recording, token=self.token)
                           for recording in data.get("recording_files", [])]

    def download_recordings(self, index=None):
        for idx, recording in enumerate(self.recordings):
            if index and idx != index:
                continue
            resp = self.__zoom.get_recording(recording)
            with open("./%s" % recording.name, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=128):
                    fh.write(chunk)

    def delete_recordings(self):
        self.__zoom.delete("meetings/%s/recordings" % self.id)


class Recording:
    RecordingType = {
        "shared_screen_with_gallery_view": "Gallery Video",
        "shared_screen_with_speaker_view": "Speaker Video",
        "audio_only": "Session Audio",
    }

    def __init__(self, client, meeting, data, token=None):
        self.id = data["id"]
        self.__zoom = client
        self.meeting = meeting
        self.start = arrow.get(data["recording_start"])
        self.end = arrow.get(data["recording_end"])
        self.type = data["recording_type"]
        self.ext = data["file_type"].lower()
        self.url = data["download_url"]
        self.size = data["file_size"]
        self.token = token
        self._data = data

    def __repr__(self):
        return "<Recording - %s>" % (self.name)

    def get_handle(self):
        return self.__zoom.get_recording(self, access_token=self.token)

    def delete(self):
        self.__zoom.delete("meetings/%s/recordings/%s" % (self.meeting.id, self.id))

    @property
    def name(self):
        return "%(start)s %(type)s.%(ext)s" % {
            "start": self.start.to('EST').strftime("%Y-%m-%d %H%M%Z"),
            "type": self.RecordingType.get(self.type, self.type),
            "ext": self.ext
        }

    @property
    def meta(self):
        return {
            "meeting": str(self.meeting.id),
            "year": str(self.start.year),
            "month": str(self.start.month),
            "day": str(self.start.day),
            "timestamp": str(self.start.timestamp),
            "type": self.RecordingType.get(self.type, self.type),
            "format": "audio" if self.ext == "m4a" else "video",
            "id": self.id,
            "size": filesize.naturalsize(self.size)
        }
