import requests


class ApiError(RuntimeError):
    pass


def get_json(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 8) -> dict:
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ApiError(str(exc)) from exc


def post_json(url: str, payload: dict | None = None, headers: dict | None = None, timeout: int = 12) -> dict:
    try:
        response = requests.post(url, json=payload or {}, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        raise ApiError(str(exc)) from exc
