from os import environ
import json
import logging
import math
import random
import requests

ID_LEN = 22
PLAYLIST_NAME = "A Random randomness"


class Spotify_Handler:
    def __init__(self):
        self.playlist_size = 100
        self.logger = logging.getLogger("Spotify_Handler")
        self.base_url = "https://api.spotify.com"
        self.playlist_url = f"{self.base_url}/v1/me/playlists"
        self.tracks_url = None
        self.session = requests.Session()
        self.__set_session_headers()
        self.__check_token()
        self.playlist_id = None

    def __check_token(self):
        headers = {"Accept": "application/json"}
        self.logger.info("Checking if 'SPOTIFY_OAUTH_TOKEN' is still alive")
        response = self.session.get(self.playlist_url, headers=headers)
        response.raise_for_status()

    def __set_session_headers(self):
        if "SPOTIFY_OAUTH_TOKEN" in environ:
            self.session.headers.update(
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {environ['SPOTIFY_OAUTH_TOKEN']}",
                }
            )
        else:
            raise ValueError("environment variable 'SPOTIFY_OAUTH_TOKEN' is undefined")

    def __set_playlistid(self, playlist_id: str):
        if playlist_id:
            self.playlist_id = playlist_id
            self.tracks_url = f"{self.base_url}/v1/playlists/{self.playlist_id}/tracks"
        else:
            self.playlist_id = None
            self.tracks_url = None

    def __save_tracks(self, track_list: list):
        headers = {"Accept": "application/json"}
        data = {"uris": track_list}
        response = self.session.post(self.tracks_url, headers=headers, data=json.dumps(data))
        response.raise_for_status()

    def __break_list(self, track_list: list, size: int = 0) -> list:
        broken_track_list = []
        if size:
            playlist_size = size
        else:
            playlist_size = self.playlist_size

        if len(track_list) <= playlist_size:
            broken_track_list.append(track_list)
        else:
            length = len(track_list)
            turns = math.ceil(length / playlist_size)
            for item in range(turns):
                start = item * playlist_size
                end = (item + 1) * playlist_size
                end = end if end <= len(track_list) else len(track_list)
                broken_track_list.append(track_list[start:end])
        return broken_track_list

    def playlist_exists(self, playlist_id: str) -> bool:
        exists = False
        url = f"{self.base_url}/v1/playlists/{playlist_id}"
        headers = {"Accept": "application/json"}
        self.logger.info(f"Checking if playlist '{playlist_id}' exists")
        response = self.session.get(url, headers=headers)
        response.raise_for_status()
        if response.status_code == 200:
            exists = True
        return exists

    def set_playlist_id(self, playlist_id: str):
        if isinstance(playlist_id, str):
            if len(playlist_id) == ID_LEN and self.playlist_exists(playlist_id):
                self.__set_playlistid(playlist_id)
            else:
                raise ValueError("playlist_id is an invalid id")
        else:
            raise TypeError("playlist_id should be type str")

    def get_playlist(self) -> str:
        next_url = f"{self.playlist_url}?limit=50"
        headers = {"Accept": "application/json"}
        self.__set_playlistid("")
        while next_url and not self.playlist_id:
            self.logger.info("Getting user's playlist list")
            response = self.session.get(next_url, headers=headers)
            response.raise_for_status()
            if response.status_code == 200:
                response_dict = response.json()
                next_url = response_dict["next"]
                for item in response_dict["items"]:
                    if item["name"] == PLAYLIST_NAME:
                        self.__set_playlistid(item["id"])
            else:
                next_url = False
        return self.playlist_id

    def create_playlist(self) -> str:
        data = {
            "name": PLAYLIST_NAME,
            "public": False,
            "description": "This play list was created by a bot",
        }
        self.__set_playlistid("")
        self.logger.info("Creating new playlist")
        response = self.session.post(self.playlist_url, data=json.dumps(data))
        response.raise_for_status()
        if response.status_code == 200 or response.status_code == 201:
            response_dict = response.json()
            self.__set_playlistid(response_dict["id"])
        return self.playlist_id

    def __del_tracks(self, track_list: list):
        data = {"tracks": []}
        for track in track_list:
            data["tracks"].append({"uri": track})
        response = self.session.delete(self.tracks_url, data=json.dumps(data))
        response.raise_for_status()

    def del_tracks_from_playlist(self, track_list: list):
        if isinstance(track_list, list) and track_list:
            self.logger.info(
                f"Deleting {len(track_list)} tracks from playlist '{self.playlist_id}'"
            )
            broken_list = self.__break_list(track_list)
            for item in broken_list:
                self.__del_tracks(item)
        else:
            raise TypeError("del_tracks_from_playlist() was called with the wrong value")

    def save_tracks_to_playlist(self, track_list: list):
        if isinstance(track_list, list) and track_list:
            self.logger.info(f"Saving {len(track_list)} tracks to playlist '{self.playlist_id}'")
            broken_list = self.__break_list(track_list)
            for item in broken_list:
                self.__save_tracks(item)

    def get_random_track(self, track_list: list) -> list:
        random_list = []
        if isinstance(track_list, list) and track_list:
            size = self.playlist_size * 2
            self.logger.info(f"{size} tracks were randomly generated")
            random_list = random.sample(track_list, k=size)
        else:
            raise TypeError("get_random_track() was called with the wrong value")
        return random_list

    def get_tracks(self, playlist: bool = False) -> list:
        track_list = []
        headers = {"Accept": "application/json"}
        if playlist:
            next_url = f"{self.tracks_url}?fields=next,items(track.uri)&limit=100"
            self.logger.info(f"Getting tracks from playlist '{self.playlist_id}'")
        else:
            next_url = f"{self.base_url}/v1/me/tracks?limit=50"
            self.logger.info("Getting new load of tracks from Spotify API...")
        total = 0
        while next_url:
            response = self.session.get(next_url, headers=headers)
            response.raise_for_status()
            if response.status_code == 200:
                response_dict = response.json()
                next_url = response_dict["next"]
                for item in response_dict["items"]:
                    total += 1
                    track_list.append(item["track"]["uri"])
            else:
                next_url = False
        self.logger.info(f"tracks count is {total}")
        return track_list


def main():
    spoty = Spotify_Handler()
    spoty.get_playlist()
    spoty.get_tracks()


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    main()
