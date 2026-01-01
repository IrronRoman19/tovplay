from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create the limiter instance, but don't attach it to an app yet
limiter = Limiter(
    get_remote_address,
    storage_options={"socket_connect_timeout": 30},
    strategy="fixed-window"
)