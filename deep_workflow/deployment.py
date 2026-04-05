from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit

DEPLOYMENT_URL_KEYS = (
    "APP_BASE_URL",
    "VERCEL_PROJECT_PRODUCTION_URL",
    "VERCEL_BRANCH_URL",
    "VERCEL_URL",
)
DEPLOYMENT_ENVIRONMENTS = {"preview", "production", "development"}
HSTS_PRELOAD_MIN_SECONDS = 31536000


def default_debug(environ: Mapping[str, str]) -> bool:
    return environ.get("VERCEL_ENV", "").strip().lower() not in {
        "preview",
        "production",
    } and environ.get("VERCEL", "").strip().lower() not in {"1", "true"}


def hsts_preload_enabled(
    *,
    preload_opt_in: bool,
    secure_hsts_seconds: int,
    include_subdomains: bool,
) -> bool:
    return (
        preload_opt_in
        and secure_hsts_seconds >= HSTS_PRELOAD_MIN_SECONDS
        and include_subdomains
    )


def deployment_environment(environ: Mapping[str, str]) -> str:
    vercel_environment = environ.get("VERCEL_ENV", "").strip().lower()
    if vercel_environment in DEPLOYMENT_ENVIRONMENTS:
        return vercel_environment
    return "local"


def hosted_environment(environ: Mapping[str, str]) -> bool:
    return deployment_environment(environ) in {"preview", "production"} or bool(
        environ.get("APP_BASE_URL", "").strip()
    )


def deployment_git_sha(environ: Mapping[str, str]) -> str:
    return (
        environ.get("VERCEL_GIT_COMMIT_SHA", "").strip()
        or environ.get("GITHUB_SHA", "").strip()
    )


def canonical_deployment_url(environ: Mapping[str, str]) -> str:
    url_keys = DEPLOYMENT_URL_KEYS
    if deployment_environment(environ) == "preview":
        url_keys = (
            "VERCEL_BRANCH_URL",
            "VERCEL_URL",
            "APP_BASE_URL",
            "VERCEL_PROJECT_PRODUCTION_URL",
        )
    for key in url_keys:
        if origin := normalize_origin(environ.get(key, "")):
            return origin
    return ""


def build_allowed_hosts(
    configured_hosts: Iterable[str], environ: Mapping[str, str]
) -> list[str]:
    hosts = []
    for value in configured_hosts:
        if host := normalize_host(value):
            hosts.append(host)
    for key in DEPLOYMENT_URL_KEYS:
        if host := normalize_host(environ.get(key, "")):
            hosts.append(host)
    return dedupe(hosts)


def build_csrf_trusted_origins(
    configured_origins: Iterable[str], environ: Mapping[str, str]
) -> list[str]:
    origins = []
    for value in configured_origins:
        if origin := normalize_origin(value):
            origins.append(origin)
    for key in DEPLOYMENT_URL_KEYS:
        if origin := normalize_origin(environ.get(key, "")):
            origins.append(origin)
    return dedupe(origins)


def normalize_host(value: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        return ""
    if normalized_value == "*" or normalized_value.startswith("."):
        return normalized_value
    if "://" in normalized_value:
        parsed_value = urlsplit(normalized_value)
        normalized_value = parsed_value.netloc or parsed_value.path
    normalized_value = normalized_value.split("/", maxsplit=1)[0]
    normalized_value = normalized_value.split("@", maxsplit=1)[-1]
    if normalized_value.startswith("[") and "]" in normalized_value:
        normalized_value = normalized_value[1 : normalized_value.index("]")]
    elif normalized_value.count(":") == 1:
        normalized_value = normalized_value.rsplit(":", maxsplit=1)[0]
    return normalized_value.lower()


def normalize_origin(value: str, default_scheme: str = "https") -> str:
    normalized_value = value.strip().rstrip("/")
    if not normalized_value:
        return ""
    if "://" in normalized_value:
        parsed_value = urlsplit(normalized_value)
        if parsed_value.scheme and parsed_value.netloc:
            return f"{parsed_value.scheme}://{parsed_value.netloc}".lower()
        return ""
    if host := normalize_host(normalized_value):
        return f"{default_scheme}://{host}".lower()
    return ""


def dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    deduped_values: list[str] = []

    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped_values.append(value)

    return deduped_values
