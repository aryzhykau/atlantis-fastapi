import pytest
from datetime import time, date, timedelta
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.models import TrainingTemplate, TrainingStudentTemplate, User, TrainingType, Student
from app.models.user import UserRole
from app.schemas.training_template import (
    TrainingTemplateCreate,
    TrainingTemplateUpdate,
    TrainingStudentTemplateCreate,
    TrainingStudentTemplateUpdate,
)
from app.crud.training_template import (
    create_training_template,
    get_training_template_by_id,
    update_training_template,
    delete_training_template,
    create_training_student_template,
    get_training_student_template_by_id,
    update_training_student_template,
    delete_training_student_template,
)


@pytest.fixture
def test_trainer(db_session: Session) -> User:
    trainer = User(
        first_name="Тренер",
        last_name="Тестов",
        email="trainer@test.com",
        phone="+79999999999",
        date_of_birth=date(1990, 1, 1),
        role=UserRole.TRAINER
    )
    db_session.add(trainer)
    db_session.commit()
    db_session.refresh(trainer)
    return trainer


@pytest.fixture
def test_client(db_session: Session) -> User:
    client = User(
        first_name="Клиент",
        last_name="Тестов",
        email="client@test.com",
        phone="+79999999998",
        date_of_birth=date(1990, 1, 1),
        role=UserRole.CLIENT
    )
    db_session.add(client)
    db_session.commit()
    db_session.refresh(client)
    return client


@pytest.fixture
def test_student(db_session: Session, test_client: User) -> Student:
    student = Student(
        first_name="Студент",
        last_name="Тестов",
        date_of_birth=date(2010, 1, 1),
        client_id=test_client.id
    )
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)
    return student


@pytest.fixture
def test_training_type(db_session: Session) -> TrainingType:
    training_type = TrainingType(
        name="Тестовая тренировка",
        is_subscription_only=False,
        price=1000.00,
        color="#FF0000"
    )
    db_session.add(training_type)
    db_session.commit()
    db_session.refresh(training_type)
    return training_type


@pytest.fixture
def test_template(db_session: Session, test_trainer: User, test_training_type: TrainingType) -> TrainingTemplate:
    template_data = TrainingTemplateCreate(
        day_number=1,
        start_time=time(10, 0),
        responsible_trainer_id=test_trainer.id,
        training_type_id=test_training_type.id
    )
    return create_training_template(db_session, template_data)


@pytest.fixture
def test_student_template(
    db_session: Session,
    test_template: TrainingTemplate,
    test_student: Student
) -> TrainingStudentTemplate:
    student_template_data = TrainingStudentTemplateCreate(
        training_template_id=test_template.id,
        student_id=test_student.id,
        start_date=date.today() + timedelta(days=1)
    )
    return create_training_student_template(db_session, student_template_data)


class TestTrainingTemplate:
    def test_create_template(self, db_session: Session, test_trainer: User, test_training_type: TrainingType):
        template_data = TrainingTemplateCreate(
            day_number=1,
            start_time=time(10, 0),
            responsible_trainer_id=test_trainer.id,
            training_type_id=test_training_type.id
        )
        template = create_training_template(db_session, template_data)
        
        assert template.day_number == 1
        assert template.start_time == time(10, 0)
        assert template.responsible_trainer_id == test_trainer.id
        assert template.training_type_id == test_training_type.id

    def test_create_template_invalid_day(self, db_session: Session, test_trainer: User, test_training_type: TrainingType):
        with pytest.raises(ValidationError, match="Input should be less than or equal to 7"):
            TrainingTemplateCreate(
                day_number=8,
                start_time=time(10, 0),
                responsible_trainer_id=test_trainer.id,
                training_type_id=test_training_type.id
            )

    def test_create_template_invalid_time(self, db_session: Session, test_trainer: User, test_training_type: TrainingType):
        with pytest.raises(ValueError, match="Время тренировки должно быть в интервале с 6:00 до 23:00"):
            TrainingTemplateCreate(
                day_number=1,
                start_time=time(5, 0),
                responsible_trainer_id=test_trainer.id,
                training_type_id=test_training_type.id
            )

    def test_update_template(self, db_session: Session, test_template: TrainingTemplate):
        update_data = TrainingTemplateUpdate(
            day_number=2,
            start_time=time(11, 0)
        )
        updated_template = update_training_template(db_session, test_template.id, update_data)
        
        assert updated_template.day_number == 2
        assert updated_template.start_time == time(11, 0)
        assert updated_template.responsible_trainer_id == test_template.responsible_trainer_id
        assert updated_template.training_type_id == test_template.training_type_id

    def test_delete_template(self, db_session: Session, test_template: TrainingTemplate):
        deleted_template = delete_training_template(db_session, test_template.id)
        assert deleted_template.id == test_template.id
        
        template = get_training_template_by_id(db_session, test_template.id)
        assert template is None


class TestTrainingStudentTemplate:
    def test_create_student_template(
        self,
        db_session: Session,
        test_template: TrainingTemplate,
        test_student: Student
    ):
        tomorrow = date.today() + timedelta(days=1)
        student_template_data = TrainingStudentTemplateCreate(
            training_template_id=test_template.id,
            student_id=test_student.id,
            start_date=tomorrow
        )
        student_template = create_training_student_template(db_session, student_template_data)
        
        assert student_template.training_template_id == test_template.id
        assert student_template.student_id == test_student.id
        assert student_template.start_date == tomorrow
        assert not student_template.is_frozen
        assert student_template.freeze_start_date is None
        assert student_template.freeze_duration_days is None

    def test_create_student_template_past_date(
        self,
        db_session: Session,
        test_template: TrainingTemplate,
        test_student: Student
    ):
        yesterday = date.today() - timedelta(days=1)
        with pytest.raises(ValueError, match="Дата начала не может быть в прошлом"):
            TrainingStudentTemplateCreate(
                training_template_id=test_template.id,
                student_id=test_student.id,
                start_date=yesterday
            )

    def test_freeze_student_template(self, db_session: Session, test_student_template: TrainingStudentTemplate):
        tomorrow = date.today() + timedelta(days=1)
        update_data = TrainingStudentTemplateUpdate(
            is_frozen=True,
            freeze_start_date=tomorrow,
            freeze_duration_days=14
        )
        updated_template = update_training_student_template(
            db_session,
            test_student_template.id,
            update_data
        )
        
        assert updated_template.is_frozen
        assert updated_template.freeze_start_date == tomorrow
        assert updated_template.freeze_duration_days == 14

    def test_freeze_student_template_without_date(
        self,
        db_session: Session,
        test_student_template: TrainingStudentTemplate
    ):
        with pytest.raises(ValueError, match="При заморозке необходимо указать дату начала заморозки"):
            TrainingStudentTemplateUpdate(
                is_frozen=True,
                freeze_duration_days=14
            )

    def test_freeze_student_template_without_duration(
        self,
        db_session: Session,
        test_student_template: TrainingStudentTemplate
    ):
        tomorrow = date.today() + timedelta(days=1)
        with pytest.raises(ValueError, match="При заморозке необходимо указать длительность заморозки"):
            TrainingStudentTemplateUpdate(
                is_frozen=True,
                freeze_start_date=tomorrow
            )

    def test_freeze_student_template_past_date(
        self,
        db_session: Session,
        test_student_template: TrainingStudentTemplate
    ):
        yesterday = date.today() - timedelta(days=1)
        with pytest.raises(ValueError, match="Дата начала заморозки не может быть в прошлом"):
            TrainingStudentTemplateUpdate(
                is_frozen=True,
                freeze_start_date=yesterday,
                freeze_duration_days=14
            )

    def test_delete_student_template(
        self,
        db_session: Session,
        test_student_template: TrainingStudentTemplate
    ):
        deleted_template = delete_training_student_template(db_session, test_student_template.id)
        assert deleted_template.id == test_student_template.id
        
        template = get_training_student_template_by_id(db_session, test_student_template.id)
        assert template is None 