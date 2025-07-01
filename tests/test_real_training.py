import pytest
from datetime import date, time, timedelta
from sqlalchemy.orm import Session

from app.crud.real_training import generate_next_week_trainings
from app.crud.training_template import create_training_template, create_training_student_template
from app.models import TrainingType, Student, RealTrainingStudent, TrainingStudentTemplate
from app.schemas.training_template import TrainingTemplateCreate, TrainingStudentTemplateCreate


def test_generate_next_week_trainings_with_limits_and_start_date(
    db_session: Session,
    test_trainer, 
    test_client,
    caplog
):
    """
    Тест проверяет логику generate_next_week_trainings:
    - Учитывает start_date студента в шаблоне.
    - Учитывает max_participants из типа тренировки.
    - Логирует предупреждение, если студент не добавлен из-за лимита.
    """
    # 1. SETUP
    # Создаем тип тренировки с лимитом 2
    limited_training_type = TrainingType(
        name="Limited Group",
        is_subscription_only=False,
        price=150.0,
        color="#LG",
        max_participants=2
    )
    db_session.add(limited_training_type)
    db_session.commit()

    # Создаем шаблон для следующего понедельника
    today = date.today()
    next_monday = today + timedelta(days=(7 - today.weekday()))
    
    template = create_training_template(db_session, TrainingTemplateCreate(
        day_number=1, # Понедельник
        start_time=time(9, 0),
        responsible_trainer_id=test_trainer.id,
        training_type_id=limited_training_type.id
    ))

    # Создаем 4 студентов
    students = [
        Student(first_name=f"Student{i}", last_name="Test", client_id=test_client.id, date_of_birth=date(2010, 1, i+1))
        for i in range(4)
    ]
    db_session.add_all(students)
    db_session.commit()

    # Привязываем студентов к шаблону с разными датами начала напрямую в БД, обходя Pydantic-валидацию
    # Студент 0: должен попасть (start_date в прошлом)
    db_session.add(TrainingStudentTemplate(
        training_template_id=template.id, student_id=students[0].id, start_date=today - timedelta(days=5)
    ))
    # Студент 1: должен попасть (start_date в день тренировки)
    db_session.add(TrainingStudentTemplate(
        training_template_id=template.id, student_id=students[1].id, start_date=next_monday
    ))
    # Студент 2: НЕ должен попасть (start_date в будущем)
    db_session.add(TrainingStudentTemplate(
        training_template_id=template.id, student_id=students[2].id, start_date=next_monday + timedelta(days=1)
    ))
    # Студент 3: НЕ должен попасть (лимит участников)
    db_session.add(TrainingStudentTemplate(
        training_template_id=template.id, student_id=students[3].id, start_date=today - timedelta(days=10)
    ))
    db_session.commit()

    # 2. ACTION
    created_count, created_trainings = generate_next_week_trainings(db_session)
    
    # 3. ASSERT
    # Была создана 1 тренировка
    assert created_count == 1
    assert len(created_trainings) == 1
    new_training = created_trainings[0]

    # В ней 2 студента (согласно лимиту)
    training_participants = db_session.query(RealTrainingStudent).filter(
        RealTrainingStudent.real_training_id == new_training.id
    ).all()
    assert len(training_participants) == 2

    # Проверяем, что это правильные студенты
    participant_ids = {p.student_id for p in training_participants}
    assert students[3].id in participant_ids # Студент 3 должен быть (самая ранняя дата)
    assert students[0].id in participant_ids # Студент 0 должен быть (второй по дате)
    assert students[1].id not in participant_ids # Студент 1 не должен быть (из-за лимита)
    assert students[2].id not in participant_ids # Студент 2 не должен быть (будущая дата)

    # Проверяем лог
    assert "was not added to RealTraining ID" in caplog.text
    assert "because max_participants (2) was reached" in caplog.text
    assert f"Student ID {students[1].id}" in caplog.text 