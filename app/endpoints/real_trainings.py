from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from app.auth.jwt_handler import verify_jwt_token
from app.dependencies import get_db
from app.schemas.real_training import (
    RealTrainingCreate,
    RealTrainingUpdate,
    RealTrainingResponse,
    RealTrainingStudentCreate,
    RealTrainingStudentUpdate,
    RealTrainingStudentResponse,
)
from app.schemas.user import UserRole
from app.crud.real_training import (
    get_real_trainings,
    get_real_trainings_with_students,
    get_real_training,
    create_real_training,
    update_real_training,
    delete_real_training,
    add_student_to_training,
    update_student_attendance,
    remove_student_from_training,
    generate_next_week_trainings,
)

router = APIRouter(prefix="/real-trainings", tags=["Real Trainings"])


# Получение списка тренировок с фильтрами
@router.get("/", response_model=list[RealTrainingResponse])
def get_trainings_endpoint(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    trainer_id: Optional[int] = None,
    training_type_id: Optional[int] = None,
    include_cancelled: bool = False,
    with_students: bool = False,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Получает список реальных тренировок с возможностью фильтрации:
    - По периоду (start_date, end_date)
    - По тренеру (trainer_id)
    - По типу тренировки (training_type_id)
    - С учетом или без учета отмененных тренировок (include_cancelled)
    - С загрузкой или без загрузки студентов (with_students)
    """
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(
            status_code=403,
            detail="Только администраторы и тренеры могут просматривать тренировки"
        )

    # Если текущий пользователь - тренер, он может видеть только свои тренировки
    if current_user["role"] == UserRole.TRAINER:
        trainer_id = current_user["user_id"]

    if with_students:
        return get_real_trainings_with_students(
            db,
            start_date=start_date,
            end_date=end_date,
            trainer_id=trainer_id,
            training_type_id=training_type_id,
            include_cancelled=include_cancelled,
        )
    else:
        return get_real_trainings(
            db,
            start_date=start_date,
            end_date=end_date,
            trainer_id=trainer_id,
            training_type_id=training_type_id,
            include_cancelled=include_cancelled,
        )


# Получение конкретной тренировки
@router.get("/{training_id}", response_model=RealTrainingResponse)
def get_training_endpoint(
    training_id: int,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Получает информацию о конкретной тренировке по её ID."""
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(
            status_code=403,
            detail="Только администраторы и тренеры могут просматривать тренировки"
        )

    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    # Тренер может видеть только свои тренировки
    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["user_id"]):
        raise HTTPException(
            status_code=403,
            detail="У вас нет доступа к этой тренировке"
        )

    return training


# Создание новой тренировки
@router.post("/", response_model=RealTrainingResponse, status_code=201)
def create_training_endpoint(
    training_data: RealTrainingCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Создает новую реальную тренировку.
    Если указан template_id, автоматически копирует студентов из шаблона.
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Только администратор может создавать тренировки"
        )

    try:
        return create_real_training(db, training_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Обновление тренировки
@router.put("/{training_id}", response_model=RealTrainingResponse)
def update_training_endpoint(
    training_id: int,
    training_data: RealTrainingUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Обновляет информацию о тренировке.
    При указании причины отмены тренировка помечается как отмененная.
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Только администратор может обновлять тренировки"
        )

    training = update_real_training(db, training_id, training_data)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
    return training


# Удаление тренировки
@router.delete("/{training_id}", response_model=RealTrainingResponse)
def delete_training_endpoint(
    training_id: int,
    delete_future: bool = False,
    template_id: Optional[int] = None,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Удаляет тренировку.
    При delete_future=True и указанном template_id удаляет все будущие тренировки из этого шаблона.
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Только администратор может удалять тренировки"
        )

    training = delete_real_training(
        db,
        training_id,
        delete_future=delete_future,
        template_id=template_id
    )
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
    return training


# Добавление студента на тренировку
@router.post("/{training_id}/students", response_model=RealTrainingStudentResponse)
def add_student_endpoint(
    training_id: int,
    student_data: RealTrainingStudentCreate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """Добавляет студента на тренировку."""
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(
            status_code=403,
            detail="Только администраторы и тренеры могут добавлять студентов"
        )

    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    # Тренер может добавлять студентов только на свои тренировки
    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["user_id"]):
        raise HTTPException(
            status_code=403,
            detail="Вы можете добавлять студентов только на свои тренировки"
        )

    student = add_student_to_training(db, training_id, student_data)
    if not student:
        raise HTTPException(
            status_code=400,
            detail="Не удалось добавить студента на тренировку"
        )
    return student


# Отметка посещаемости студента
@router.put(
    "/{training_id}/students/{student_id}/attendance",
    response_model=RealTrainingStudentResponse
)
def update_attendance_endpoint(
    training_id: int,
    student_id: int,
    attendance_data: RealTrainingStudentUpdate,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Обновляет статус посещения студента.
    При отмене автоматически проверяется необходимость оплаты штрафа.
    """
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(
            status_code=403,
            detail="Только администраторы и тренеры могут отмечать посещаемость"
        )

    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    # Тренер может отмечать посещаемость только на своих тренировках
    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["user_id"]):
        raise HTTPException(
            status_code=403,
            detail="Вы можете отмечать посещаемость только на своих тренировках"
        )

    student = update_student_attendance(
        db,
        training_id,
        student_id,
        attendance_data,
        trainer_id=current_user["user_id"]
    )
    if not student:
        raise HTTPException(
            status_code=404,
            detail="Студент не найден на этой тренировке"
        )
    return student


# Удаление студента с тренировки
@router.delete(
    "/{training_id}/students/{student_id}",
    response_model=RealTrainingStudentResponse
)
def remove_student_endpoint(
    training_id: int,
    student_id: int,
    remove_future: bool = False,
    template_id: Optional[int] = None,
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Удаляет студента с тренировки.
    При remove_future=True и указанном template_id удаляет студента со всех будущих тренировок из шаблона.
    """
    if current_user["role"] not in [UserRole.ADMIN, UserRole.TRAINER]:
        raise HTTPException(
            status_code=403,
            detail="Только администраторы и тренеры могут удалять студентов"
        )

    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    # Тренер может удалять студентов только со своих тренировок
    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["user_id"]):
        raise HTTPException(
            status_code=403,
            detail="Вы можете удалять студентов только со своих тренировок"
        )

    student = remove_student_from_training(
        db,
        training_id,
        student_id,
        remove_future=remove_future,
        template_id=template_id
    )
    if not student:
        raise HTTPException(
            status_code=404,
            detail="Студент не найден на этой тренировке"
        )
    return student


# Генерация тренировок на следующую неделю
@router.post("/generate-next-week", response_model=dict)
def generate_next_week_endpoint(
    current_user = Depends(verify_jwt_token),
    db: Session = Depends(get_db)
):
    """
    Генерирует тренировки на следующую неделю на основе активных шаблонов.
    Доступно только для администраторов.
    
    Возвращает:
    - Количество созданных тренировок
    - Период, на который созданы тренировки
    """
    if current_user["role"] != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Только администратор может генерировать тренировки"
        )

    try:
        created_count, trainings = generate_next_week_trainings(db)
        
        if created_count == 0:
            return {
                "message": "Нет новых тренировок для генерации",
                "created_count": 0,
                "period": {
                    "start": None,
                    "end": None
                }
            }
        
        return {
            "message": f"Успешно сгенерировано {created_count} тренировок",
            "created_count": created_count,
            "period": {
                "start": trainings[0].date,
                "end": trainings[-1].date
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка при генерации тренировок: {str(e)}"
        ) 