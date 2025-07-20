import unittest
from unittest.mock import MagicMock, patch
from app.services.student_service import StudentService
from app.models.student import Student
from app.models.subscription import StudentSubscription

class TestStudentService(unittest.TestCase):

    def setUp(self):
        self.db_session = MagicMock()
        self.student_service = StudentService()

    def test_update_active_subscription_id(self):
        # Arrange
        student = Student(id=1, active_subscription_id=1)
        expired_subscription = StudentSubscription(status='expired')
        active_subscription = StudentSubscription(subscription_id=2, status='active')

        self.db_session.query.return_value.filter.return_value.first.side_effect = [expired_subscription, active_subscription]

        # Act
        self.student_service.update_active_subscription_id(self.db_session, student)

        # Assert
        self.assertEqual(student.active_subscription_id, 2)
        self.db_session.commit.assert_called_once()

if __name__ == '__main__':
    unittest.main()
