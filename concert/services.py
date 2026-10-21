"""Part 3 sample data, with explicit microservice configuration for deployment."""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

SAMPLE_SONGS = [{
    "id": 1,
    "title": "duis faucibus accumsan odio curabitur convallis",
    "lyrics": "Morbi non lectus. Aliquam sit amet diam in magna bibendum imperdiet. Nullam orci pede, venenatis non, sodales sed, tincidunt eu, felis.",
}]
SAMPLE_PHOTOS = [{
    "id": 1,
    "pic_url": "http://dummyimage.com/136x100.png/5fa2dd/ffffff",
    "event_country": "United States",
    "event_state": "District of Columbia",
    "event_city": "Washington",
    "event_date": "11/16/2022",
}]


class ServiceUnavailable(Exception):
    """A configured backend did not return the required resource collection."""


def _load(base_url, endpoint, required_fields, collection_key=None):
    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/{endpoint}", timeout=settings.SERVICE_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
        if collection_key:
            data = data[collection_key]
        if not isinstance(data, list) or not all(
            isinstance(item, dict) and all(key in item for key in required_fields)
            for item in data
        ):
            raise ValueError("invalid resource collection")
        return data
    except (requests.RequestException, ValueError, TypeError, KeyError) as error:
        logger.warning("Backend %s request failed (%s)", endpoint, type(error).__name__)
        raise ServiceUnavailable from error


def load_songs():
    if not settings.SONGS_SERVICE_URL:
        return SAMPLE_SONGS
    return _load(settings.SONGS_SERVICE_URL, "song", ("id", "title", "lyrics"), "songs")


def load_photos():
    if not settings.PICTURES_SERVICE_URL:
        return SAMPLE_PHOTOS
    return _load(settings.PICTURES_SERVICE_URL, "picture", (
        "id", "pic_url", "event_country", "event_state", "event_city", "event_date"
    ))
