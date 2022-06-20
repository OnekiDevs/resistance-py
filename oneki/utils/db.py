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


class AsyncDocumentReference(firestore.firestore.AsyncDocumentReference):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def delete(self, camp=None, *args):
        if camp is not None:
            await super().update({camp: firestore.firestore.DELETE_FIELD}, *args) 
        else: await super().delete(*args)


class AsyncClient(firestore.firestore.AsyncClient):
    async_transactional = firestore.firestore.async_transactional
    
    def __init__(self, credentials=None, project=None, *args):
        super().__init__(credentials=credentials, project=project, *args)
        self.ArrayUnion = firestore.firestore.ArrayUnion
        self.ArrayRemove = firestore.firestore.ArrayRemove
        self.Increment = firestore.firestore.Increment
        self.Query = firestore.firestore.AsyncQuery
    
    def document(self, *document_path: str) -> AsyncDocumentReference:
        return AsyncDocumentReference(
            *self._document_path_helper(*document_path), client=self
        )


class _FirestoreAsyncClient:
    """Holds a async Google Cloud Firestore client instance."""
    def __init__(self, credentials, project):
        self._client = AsyncClient(credentials=credentials, project=project)

    def get(self) -> AsyncClient:
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
