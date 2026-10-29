"""Error types and user-facing messages (pt-BR)."""

MSG_INVALID = "Esse endereço não parece um link válido."
MSG_HOST = "Por enquanto só aceitamos links do Instagram, TikTok, X (Twitter) e YouTube."
MSG_UNSUPPORTED = (
    "Esse link não é compatível. Use um post, Reel ou Story público do Instagram, "
    "um vídeo do TikTok, um post com mídia do X ou um vídeo único do YouTube "
    "(não vale playlist nem live)."
)
MSG_LIVE = (
    "Transmissões ao vivo não são suportadas. Quando o vídeo terminar e ficar "
    "disponível, tente o link de novo."
)
MSG_BOT = (
    "O YouTube bloqueou a consulta deste servidor e pediu para confirmar que não "
    "somos um robô. Isso é comum em IPs de datacenter, como os do Render. Tente de "
    "novo mais tarde. O Baixa.ai não usa a sua conta para contornar esse bloqueio."
)
MSG_PRIVATE = (
    "Esse conteúdo é privado ou exige login. O Baixa.ai só baixa mídia pública, "
    "sem usar a sua conta."
)
MSG_TIMEOUT = "A busca demorou demais e foi cancelada. Tente de novo."
MSG_TOO_LARGE = "O arquivo passa do tamanho máximo permitido."
MSG_RATE = "Muitas buscas em pouco tempo. Espere alguns minutos e tente de novo."
MSG_NOT_FOUND = "Não encontramos mídia pública nesse link."
MSG_GENERIC = "Não foi possível obter a mídia agora. Tente de novo em instantes."
MSG_TOKEN = "Esse download expirou ou é inválido. Busque o link de novo."
MSG_OPTION = "Essa opção expirou. Busque o link de novo."

_BOT_MARKERS = (
    "sign in to confirm",
    "not a bot",
    "confirm you're not a bot",
    "confirm you’re not a bot",
)
_PRIVATE_MARKERS = (
    "private",
    "login",
    "sign in",
    "cookie",
    "logged in",
    "log in",
    "empty media response",
    "webpage is locked",
    "only available to",
)
_UNSUPPORTED_MARKERS = (
    "unsupported",
    "no video formats",
    "there is no video",
    "no media",
)
_NOT_FOUND_MARKERS = (
    "has been removed",
    "not found",
    "404",
    "deleted",
    "no longer available",
)


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.headers = headers or {}
        super().__init__(message)


def classify_extractor_error(exc: BaseException) -> AppError:
    if isinstance(exc, AppError):
        return exc
    if isinstance(exc, TimeoutError):
        return AppError("timeout", MSG_TIMEOUT, 504)
    text = f"{type(exc).__name__} {exc}".lower()
    if any(marker in text for marker in _BOT_MARKERS):
        return AppError("upstream_blocked", MSG_BOT, 503)
    if any(marker in text for marker in _PRIVATE_MARKERS):
        return AppError("private_content", MSG_PRIVATE, 422)
    if any(marker in text for marker in _NOT_FOUND_MARKERS):
        return AppError("not_found", MSG_NOT_FOUND, 404)
    if any(marker in text for marker in _UNSUPPORTED_MARKERS):
        return AppError("unsupported_content", MSG_UNSUPPORTED, 422)
    return AppError("extraction_failed", MSG_GENERIC, 502)
