from pydantic import BaseModel
from typing import List, TypeVar, Generic


T = TypeVar('T')

class PaginatedResponse(Generic[T], BaseModel):
    total_pages: int      # Общее количество страниц
    total_count: int      # Общее количество элементов
    page: int             # Текущая страница
    page_size: int        # Размер страницы (количество элементов на странице)
    data: List[T]         # Данные на текущей странице, тип T - универсальный

    class Config:
        orm_mode = True