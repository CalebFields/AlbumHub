import os
import base64
import urllib.request
import requests
from dotenv import load_dotenv
from html import unescape

class DiscogsClient:
    def __init__(self, logger=None):
        """
        logger: function taking a single string argument for logging (e.g. GUI log_message)
        """
        load_dotenv()
        self.key    = os.getenv('DISCOGS_KEY')
        self.secret = os.getenv('DISCOGS_SECRET')
        if not self.key or not self.secret:
            raise RuntimeError("Missing Discogs credentials in .env")
        # Logger for GUI or other output
        self.logger = logger or (lambda msg: print(msg))

    def _headers(self):
        return {
            'User-Agent':   'MusicCollectionApp/1.0',
            'Accept':       'application/json',
            'Authorization':'Discogs key={}, secret={}'.format(self.key, self.secret)
        }

    def fetch_discogs_release(self, artist, title, year=None):
        """Search Discogs and fetch top release details."""
        params = {'q': f"{title} {artist}", 'type': 'release', 'per_page': 1}
        if year:
            params['year'] = year

        try:
            r = requests.get(
                'https://api.discogs.com/database/search',
                headers=self._headers(), params=params, timeout=10
            )
            r.raise_for_status()
            results = r.json().get('results', [])
            if not results:
                self.logger(f"No Discogs release found for '{artist} - {title}'")
                return None

            rid = results[0]['id']
            r2  = requests.get(
                f'https://api.discogs.com/releases/{rid}',
                headers=self._headers(), timeout=10
            )
            r2.raise_for_status()
            return r2.json()

        except requests.HTTPError as e:
            self.logger(f"HTTPError fetching '{artist} - {title}': {e}")
        except Exception as e:
            self.logger(f"Error fetching '{artist} - {title}': {e}")
        return None

    def get_best_image_url(self, images):
        for img in images or []:
            if img.get('type') == 'primary' and img.get('uri'):
                return img['uri']
        for img in images or []:
            if img.get('uri'):
                return img['uri']
        return None

    def fetch_cover_art(self, url):
        """Fetch and base64‑encode cover art."""
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'MusicCollectionApp/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
            return base64.b64encode(data).decode('utf-8')

        except Exception as e:
            self.logger(f"Cover art error from {url}: {e}")
        return None

    def extract_release_data(self, release):
        """Extract relevant fields and parse track durations."""
        data = {
            'Genres':      ', '.join(release.get('genres', [])),
            'Styles':      ', '.join(release.get('styles', [])),
            'Label':       (release.get('labels') or [{}])[0].get('name', ''),
            'Country':     release.get('country', ''),
            'Format':      (release.get('formats') or [{}])[0].get('name', ''),
            'DiscogsYear': release.get('year', ''),
            'DiscogsID':   release.get('id', ''),
            'CoverArt':    None
        }
        img_url = self.get_best_image_url(release.get('images', []))
        if img_url:
            data['CoverArt'] = self.fetch_cover_art(img_url)

        durations = []
        for idx, track in enumerate(release.get('tracklist', []), start=1):
            title = track.get('title', '')
            raw   = track.get('duration') or '0:00'
            try:
                mins, secs = raw.split(':')
                total_sec = int(mins) * 60 + int(secs)
            except Exception:
                total_sec = 0
            durations.append({
                'track_number': idx,
                'title':        title,
                'duration_sec': total_sec
            })
        data['TracklistDurations'] = durations
        data['TracklistSummary'] = '; '.join(t['title'] for t in durations)

        return data

    def enrich_album(self, album):
        """
        Enriches `album` dict in place—adds Discogs metadata and track durations.
        """
        artist = album.get('Artist', '')
        title  = album.get('Title', '')
        year   = album.get('Release_Date', '')

        release = self.fetch_discogs_release(artist, title, year)
        if not release:
            self.logger(f"Could not find '{artist} - {title}' on Discogs.")
            return album

        try:
            details = self.extract_release_data(release)
            album.update(details)
        except Exception as e:
            self.logger(f"Error extracting data for '{artist} - {title}': {e}")

        return album
