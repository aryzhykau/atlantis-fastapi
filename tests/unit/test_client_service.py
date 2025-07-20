import unittest
from unittest.mock import MagicMock, patch
from app.services.client_service import ClientService
from app.schemas.user import ClientCreate
from app.schemas.student import StudentCreateWithoutClient

class TestClientService(unittest.TestCase):

    def setUp(self):
        self.db_session = MagicMock()
        self.client_service = ClientService()

    @patch('app.services.client_service.crud_user')
    @patch('app.services.client_service.crud_client')
    @patch('app.services.client_service.crud_student')
    def test_create_client_with_students(self, mock_crud_student, mock_crud_client, mock_crud_user):
        # Arrange
        mock_crud_user.get_user_by_email.return_value = None
        mock_crud_client.create_client.return_value = MagicMock(id=1, first_name='Test', last_name='User', date_of_birth='2000-01-01')

        client_data = ClientCreate(
            first_name='Test',
            last_name='User',
            email='test@example.com',
            phone='1234567890',
            date_of_birth='2000-01-01',
            is_student=True,
            students=[
                StudentCreateWithoutClient(first_name='Child', last_name='User', date_of_birth='2010-01-01')
            ]
        )

        # Act
        self.client_service.create_client_with_students(self.db_session, client_data)

        # Assert
        mock_crud_user.get_user_by_email.assert_called_once_with(self.db_session, email='test@example.com')
        mock_crud_client.create_client.assert_called_once_with(self.db_session, client_data)
        self.assertEqual(mock_crud_student.create_student.call_count, 2)
        self.db_session.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
