from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from typing import List, Optional

from app.auth.permissions import get_current_user
from app.core.security import verify_api_key
from app.dependencies import get_db
from app.schemas.real_training import (
    RealTrainingCreate,
    RealTrainingUpdate,
    RealTrainingResponse,
    StudentCancellationRequest,
    StudentCancellationResponse,
    TrainingCancellationRequest,
)
from app.schemas.real_training_student import (
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
    remove_student_from_training,
    generate_next_week_trainings,
)
from app.services.real_training import RealTrainingService

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
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
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
    # Если текущий пользователь - тренер, он может видеть только свои тренировки
    if current_user["role"] == UserRole.TRAINER:
        trainer_id = current_user["id"]

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
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """Получает информацию о конкретной тренировке по её ID."""

    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    # Тренер может видеть только свои тренировки (404 для безопасности)
    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["id"]):
        raise HTTPException(
            status_code=404,
            detail="Тренировка не найдена"
        )

    return training


# Создание новой тренировки
@router.post("/", response_model=RealTrainingResponse, status_code=201)
def create_training_endpoint(
    training_data: RealTrainingCreate,
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Создает новую реальную тренировку.
    Если указан template_id, автоматически копирует студентов из шаблона.
    """
    try:
        return create_real_training(db, training_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# Обновление тренировки
@router.put("/{training_id}", response_model=RealTrainingResponse)
def update_training_endpoint(
    training_id: int,
    training_data: RealTrainingUpdate,
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Обновляет информацию о тренировке.
    При указании причины отмены тренировка помечается как отмененная.
    """
    training = update_real_training(db, training_id, training_data)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
    return training


# Удаление тренировки
@router.delete("/{training_id}")
def delete_training_endpoint(
    training_id: int,
    delete_future: bool = False,
    template_id: Optional[int] = None,
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Удаляет тренировку.
    При delete_future=True и указанном template_id удаляет все будущие тренировки из этого шаблона.
    """
    success = delete_real_training(db, training_id)
    if not success:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
    return {"success": True, "id": training_id, "message": "Real training deleted successfully"}


# Добавление студента на тренировку
@router.post("/{training_id}/students", response_model=RealTrainingStudentResponse)
def add_student_endpoint(
    training_id: int,
    student_data: RealTrainingStudentCreate,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """Добавляет студента на тренировку, используя сервисный слой."""

    service = RealTrainingService(db)
    # Проверка прав тренера внутри сервиса не нужна, т.к. это логика эндпоинта
    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="Вы можете добавлять студентов только на свои тренировки"
        )

    return service.add_student_to_training(training_id, student_data)


# Отметка посещаемости студента
@router.put(
    "/{training_id}/students/{student_id}/attendance",
    response_model=RealTrainingStudentResponse
)
def update_attendance_endpoint(
    training_id: int,
    student_id: int,
    attendance_data: RealTrainingStudentUpdate,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """Обновляет статус посещения студента, используя сервисный слой."""

    # Проверка прав тренера
    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="Вы можете отмечать посещаемость только на своих тренировках"
        )

    service = RealTrainingService(db)
    return service.update_student_attendance(
        training_id=training_id,
        student_id=student_id,
        update_data=attendance_data,
        marker_id=current_user["id"]
    )


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
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Удаляет студента с тренировки.
    При remove_future=True и указанном template_id удаляет студента со всех будущих тренировок из шаблона.
    """

    training = get_real_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    # Тренер может удалять студентов только со своих тренировок
    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["id"]):
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
@router.post("/generate-next-week", response_model=dict, dependencies=[Depends(verify_api_key)])
def generate_next_week_endpoint(
    db: Session = Depends(get_db)
):
    """
    Генерирует тренировки на следующую неделю на основе активных шаблонов.
    Защищен API ключом (передается в заголовке X-API-Key).
    
    Возвращает:
    - Количество созданных тренировок
    - Список созданных тренировок
    - Период, на который созданы тренировки
    """

    try:
        created_count, trainings = generate_next_week_trainings(db)
        
        if created_count == 0:
            return {
                "message": "Нет новых тренировок для генерации",
                "created_count": 0,
                "trainings": [],
                "period": {
                    "start": None,
                    "end": None
                }
            }
        
        return {
            "message": f"Успешно сгенерировано {created_count} тренировок",
            "created_count": created_count,
            "trainings": [RealTrainingResponse.model_validate(training) for training in trainings],
            "period": {
                "start": trainings[0].training_date,
                "end": trainings[-1].training_date
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка при генерации тренировок: {str(e)}"
        )


# Отмена участия студента в тренировке
@router.delete(
    "/{training_id}/students/{student_id}/cancel",
    response_model=StudentCancellationResponse
)
def cancel_student_endpoint(
    training_id: int,
    student_id: int,
    cancellation_data: StudentCancellationRequest,
    current_user = Depends(get_current_user(["ADMIN", "TRAINER", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Отмена участия студента в тренировке с проверками:
    - Время до начала (минимум 12 часов)
    - Лимит переносов (максимум 3 в месяц)
    """

    service = RealTrainingService(db)
    training = service._get_training(db, training_id)
    if not training:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")

    # Тренер может отменять участие только на своих тренировках
    if (current_user["role"] == UserRole.TRAINER and 
        training.responsible_trainer_id != current_user["id"]):
        raise HTTPException(
            status_code=403,
            detail="Вы можете отменять участие только на своих тренировках"
        )

    result = service.cancel_student(training_id, student_id, cancellation_data, current_user["id"])
    return result


# Отмена тренировки
@router.post("/{training_id}/cancel", response_model=RealTrainingResponse)
async def cancel_training_endpoint(
    training_id: int,
    cancellation_data: TrainingCancellationRequest,
    current_user = Depends(get_current_user(["ADMIN", "OWNER"])),
    db: Session = Depends(get_db)
):
    """
    Полная отмена тренировки администратором.
    
    Процесс отмены:
    1. Проверка прав доступа (только администратор)
    2. Отмена тренировки для всех участников
    3. Запуск финансовых процессов (если process_refunds=True)
    4. Закрытие тренировки
    """
    service = RealTrainingService(db)
    return service.cancel_training(training_id, cancellation_data)

from app.services.daily_operations import DailyOperationsService

@router.post("/process-daily-operations", response_model=dict, dependencies=[Depends(verify_api_key)])
def process_daily_operations_endpoint(
    db: Session = Depends(get_db)
):
    """
    Запускает ежедневные операции по обработке тренировок.
    Защищен API ключом (передается в заголовке X-API-Key).
    """
    try:
        daily_operations_service = DailyOperationsService(db)
        daily_operations_service.process_tomorrows_trainings()
        return {"message": "Ежедневные операции успешно выполнены"}
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Ошибка при выполнении ежедневных операций: {str(e)}"
        )