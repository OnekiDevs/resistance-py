from firebase_admin import credentials, firestore
import firebase_admin

from utils import env
from json import loads


cred = credentials.Certificate(loads(env.GOOGLE_APPLICATION_CREDENTIALS))
firebase_app = firebase_admin.initialize_app(cred)


def async_client(app=None):
    """Returns a client that can be used to interact with Google Cloud Firestore.

    Args:
      app: An App instance (optional).

    Returns:
      google.cloud.firestore.Firestore: A `Firestore Client`_.

    Raises:
      ValueError: If a project ID is not specified either via options, credentials or
          environment variables, or if the specified project ID is not a valid string.
    """
    fs_client: _FirestoreAsyncClient = firestore._utils.get_app_service(app, firestore._FIRESTORE_ATTRIBUTE, _FirestoreAsyncClient.from_app)
    return fs_client.get()


class _FirestoreAsyncClient:
    """Holds a async Google Cloud Firestore client instance."""
    def __init__(self, credentials, project):
        self._client = firestore.firestore.AsyncClient(credentials=credentials, project=project)

    def get(self) -> firestore.firestore.AsyncClient:
        return self._client

    @classmethod
    def from_app(cls, app):
        """Creates a new _FirestoreClient for the specified app."""
        credentials = app.credential.get_credential()
        project = app.project_id
        if not project:
            raise ValueError(
                'Project ID is required to access Firestore. Either set the projectId option, '
                'or use service account credentials. Alternatively, set the GOOGLE_CLOUD_PROJECT '
                'environment variable.')
        return _FirestoreAsyncClient(credentials, project)
