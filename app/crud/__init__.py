from .real_training import (
    # Операции с реальными тренировками
    get_real_trainings,
    get_real_training,
    get_real_trainings_by_date,
    get_real_trainings_with_students,
    create_real_training,
    update_real_training,
    delete_real_training,
    
    # Операции со студентами на тренировках
    get_real_training_students,
    get_student_real_trainings,
    remove_student_from_training,
    
)
from .student import (
    create_student,
    # ... existing code ...
)
